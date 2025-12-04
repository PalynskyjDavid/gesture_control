import cv2
import math
import numpy as np


def midpoint(a, b):
    return (a + b) * 0.5


def normalize(v):
    n = np.linalg.norm(v)
    if n == 0:
        return v
    return v / n


def project_normalized_point(point, frame_shape, depth_strength=0.8):
    """
    Convert normalized Mediapipe coordinates (0..1) plus depth into pixel space
    with a lightweight perspective tweak so nearer points spread out more.
    """
    h, w, _ = frame_shape
    x, y, z = point
    perspective = 1.0 / max(1e-3, 1.0 + z * depth_strength)
    proj_x = (x - 0.5) * perspective + 0.5
    proj_y = (y - 0.5) * perspective + 0.5
    return int(proj_x * w), int(proj_y * h)


def rotate_vector(v, axis, theta_deg):
    theta = np.deg2rad(theta_deg)
    axis = normalize(axis)
    v = v.astype(float)

    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    term1 = v * cos_t
    term2 = np.cross(axis, v) * sin_t
    term3 = axis * np.dot(axis, v) * (1 - cos_t)

    return term1 + term2 + term3


def get_point(hand_data, index):
    lm = hand_data.raw_landmarks.landmark[index]
    return np.array([lm.x, lm.y, lm.z], dtype=float)


def build_tilted_plane(hand_data, indexes, tiltPointIndex, tiltAngleDeg):
    # extract points A, B, C correctly
    A = get_point(hand_data, indexes[0])
    B = get_point(hand_data, indexes[1])
    C = get_point(hand_data, indexes[2])

    # 1) base plane normal
    AB = B - A
    AC = C - A
    n0 = normalize(np.cross(AB, AC))

    # 2) base point = midpoint(B, C)
    P0 = midpoint(B, C)

    # 3) tilt axis is chosen point − P0
    tiltPoint = get_point(hand_data, indexes[tiltPointIndex])
    axis = normalize(tiltPoint - P0)

    # 4) rotate normal
    n_tilted = normalize(rotate_vector(n0, axis, tiltAngleDeg))

    # 5) plane scale relative to hand size
    # (VERY IMPORTANT FIX)
    hand_scale = np.linalg.norm(B - C)  # natural scale of 2 landmarks
    plane_size = hand_scale * 0.5  # tuning factor
    if plane_size < 0.005:
        plane_size = 0.005  # avoid vanishing
    if plane_size > 0.05:
        plane_size = 0.05  # avoid giant plane

    return P0, n_tilted, plane_size


def point_above_plane(point, plane_point, plane_normal):
    point = np.array([point.x, point.y, point.z], dtype=float)
    s = np.dot(plane_normal, point - plane_point)

    if s > 0:
        return +1  # above
    elif s < 0:
        return -1  # below
    else:
        return 0  # on plane


def draw_plane(
    frame, plane_point, plane_normal, plane_size, color=(0, 255, 0), thickness=2
):
    n = normalize(plane_normal)

    # pick arbitrary vector not parallel to n
    arbitrary = np.array([1, 0, 0], dtype=float)
    if abs(np.dot(arbitrary, n)) > 0.9:
        arbitrary = np.array([0, 1, 0], dtype=float)

    u = normalize(np.cross(n, arbitrary))
    v = normalize(np.cross(n, u))

    d = plane_size  # *** NEW SCALING FIX ***

    corners_3d = [
        plane_point + u * d + v * d,
        plane_point - u * d + v * d,
        plane_point - u * d - v * d,
        plane_point + u * d - v * d,
    ]

    camera_matrix = np.array(
        [[1920, 0, 1920 / 2], [0, 1080, 1080 / 2], [0, 0, 1]], dtype=np.float32
    )
    dist_coeffs = np.zeros((5, 1), dtype=np.float32)

    rvec = np.zeros((3, 1), np.float32)
    tvec = np.zeros((3, 1), np.float32)

    pts_2d, _ = cv2.projectPoints(
        np.array(corners_3d), rvec, tvec, camera_matrix, dist_coeffs
    )
    pts_2d = pts_2d.reshape(-1, 2).astype(int)

    cv2.polylines(frame, [pts_2d], True, color, thickness)


def draw_plane_fixed_pixel_size(
    frame,
    plane_point,
    plane_normal,
    pixel_size=100,  # desired plane size in pixels
    color=(0, 255, 0),
    thickness=2,
):
    # Unpack camera parameters
    camera_matrix = np.array(
        [[1920, 0, 1920 / 2], [0, 1080, 1080 / 2], [0, 0, 1]], dtype=np.float32
    )
    dist_coeffs = np.zeros((5, 1), dtype=np.float32)

    fx = camera_matrix[0, 0]

    # Depth (z) is negative in Mediapipe, use magnitude
    Z = abs(plane_point[2]) + 1e-6

    # Convert 100px → 3D world-size
    half_px = pixel_size / 2.0
    world_half_size = (half_px * Z) / fx

    n = normalize(plane_normal)

    # pick arbitrary vector not parallel to n
    arbitrary = np.array([1, 0, 0], dtype=float)
    if abs(np.dot(arbitrary, n)) > 0.9:
        arbitrary = np.array([0, 1, 0], dtype=float)

    # Build local plane basis
    u = normalize(np.cross(n, arbitrary))
    v = normalize(np.cross(n, u))

    d = world_half_size

    corners_3d = [
        plane_point + u * d + v * d,
        plane_point - u * d + v * d,
        plane_point - u * d - v * d,
        plane_point + u * d - v * d,
    ]

    rvec = np.zeros((3, 1), np.float32)
    tvec = np.zeros((3, 1), np.float32)

    pts_2d, _ = cv2.projectPoints(
        np.array(corners_3d), rvec, tvec, camera_matrix, dist_coeffs
    )
    pts_2d = pts_2d.reshape(-1, 2).astype(int)

    cv2.polylines(frame, [pts_2d], True, color, thickness)


def draw_debug_reference_plane(
    frame,
    hand_data=None,
    landmark_index=9,
    pixel_size=200,
    color=(255, 0, 255),
    thickness=2,
):
    """
    Draw a debug square for visualizing palm alignment. When hand data is
    available the plane is oriented by the wrist/index/pinky MCP points; otherwise
    it falls back to a screen-centered square.
    """
    h, w, _ = frame.shape

    if not (hand_data and hand_data.raw_landmarks):
        _draw_screen_space_square((w // 2, h // 2), pixel_size, frame, color, thickness)
        return None, None

    lm = hand_data.raw_landmarks.landmark
    try:
        center_pt = np.array(
            [lm[landmark_index].x, lm[landmark_index].y, lm[landmark_index].z],
            dtype=float,
        )
        wrist = get_point(hand_data, 0)
        index_base = get_point(hand_data, 5)
        pinky_base = get_point(hand_data, 17)
    except (IndexError, AttributeError):
        _draw_screen_space_square((w // 2, h // 2), pixel_size, frame, color, thickness)
        return None, None

    u = normalize(index_base - wrist)
    v = normalize(pinky_base - wrist)
    normal = normalize(np.cross(u, v))
    if np.linalg.norm(normal) < 1e-5:
        _draw_screen_space_square((w // 2, h // 2), pixel_size, frame, color, thickness)
        return None, None

    tangent = normalize(index_base - wrist)

    width_axis = normalize(pinky_base - index_base)
    if np.linalg.norm(width_axis) < 1e-5:
        width_axis = normalize(np.cross(normal, tangent))
    bitangent = normalize(np.cross(normal, tangent))
    if np.linalg.norm(bitangent) < 1e-5:
        bitangent = normalize(np.cross(normal, np.array([0.0, 0.0, 1.0])))

    upright_axis = normalize(rotate_vector(normal, tangent, -90.0))
    if np.linalg.norm(upright_axis) < 1e-5:
        upright_axis = bitangent

    depth_scale = 1.0 + (-center_pt[2]) * 1.5
    depth_scale = max(0.4, min(depth_scale, 3.0))
    base_extent = (pixel_size * depth_scale) / max(w, h)

    width_offsets = [
        abs(np.dot(index_base - center_pt, width_axis)),
        abs(np.dot(pinky_base - center_pt, width_axis)),
    ]
    half_width = max([base_extent] + width_offsets)
    half_height = base_extent

    corners = [
        center_pt + width_axis * half_width + upright_axis * half_height,
        center_pt - width_axis * half_width + upright_axis * half_height,
        center_pt - width_axis * half_width - upright_axis * half_height,
        center_pt + width_axis * half_width - upright_axis * half_height,
    ]

    pts = [project_normalized_point(tuple(pt), frame.shape) for pt in corners]
    cv2.polylines(frame, [np.array(pts, dtype=int)], True, color, thickness)
    plane_normal = normalize(np.cross(width_axis, upright_axis))
    return center_pt, plane_normal


def _draw_screen_space_square(center, pixel_size, frame, color, thickness):
    half = pixel_size / 2.0
    base = np.array(
        [
            [-half, -half],
            [half, -half],
            [half, half],
            [-half, half],
        ],
        dtype=float,
    )
    theta = np.deg2rad(-20)
    rot = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    rotated = base @ rot.T
    rotated[:, 0] += center[0]
    rotated[:, 1] += center[1]
    pts = np.round(rotated).astype(int)
    cv2.polylines(frame, [pts], True, color, thickness)


FINGER_TIPS = [
    ("Thumb", 4),
    ("Index", 8),
    ("Middle", 12),
    ("Ring", 16),
    ("Pinky", 20),
]


def annotate_fingertip_plane_status(
    frame,
    hand_data,
    plane_point,
    plane_normal,
    origin=(10, 360),
    color=(255, 255, 0),
):
    if (
        plane_point is None
        or plane_normal is None
        or hand_data is None
        or hand_data.raw_landmarks is None
    ):
        return

    lm = hand_data.raw_landmarks.landmark
    statuses = []
    for name, idx in FINGER_TIPS:
        if idx >= len(lm):
            continue
        tip = np.array([lm[idx].x, lm[idx].y, lm[idx].z], dtype=float)
        signed = np.dot(plane_normal, tip - plane_point)
        if abs(signed) < 1e-3:
            state = "on"
        elif signed > 0:
            state = "above"
        else:
            state = "below"
        statuses.append(f"{name}: {state}")

    for i, line in enumerate(statuses):
        cv2.putText(
            frame,
            line,
            (origin[0], origin[1] + i * 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            1,
            cv2.LINE_AA,
        )


def build_and_draw_tilted_plane(
    frame,
    hand_data,
    indexes=[0, 9, 5],
    tiltPointIndex=0,
    tiltAngleDeg=-10,
    color=(0, 255, 0),
    thickness=2,
):

    plane_point, plane_normal, plane_size = build_tilted_plane(
        hand_data, indexes, tiltPointIndex, tiltAngleDeg
    )

    # draw_plane(
    #     frame, plane_point, plane_normal, plane_size, color=color, thickness=thickness
    # )
    draw_plane_fixed_pixel_size(
        frame, plane_point, plane_normal, color=color, thickness=thickness
    )

    return plane_point, plane_normal
