import cv2
import math

# --------------------------------------------------------
# VECTOR MATH HELPERS
# --------------------------------------------------------
def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def vec_mul(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)

def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    )

def normalize(v):
    l = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
    if l < 1e-9: return (0,0,0)
    return (v[0]/l, v[1]/l, v[2]/l)

def rodrigues_rotation(v, k, theta_deg):
    """
    Rotates vector v around unit axis k by theta_deg degrees.
    Formula: v_rot = v*cos(t) + (k x v)*sin(t) + k*(k.v)*(1-cos(t))
    """
    theta = math.radians(theta_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    
    k_cross_v = cross(k, v)
    k_dot_v = dot(k, v)
    
    term1 = vec_mul(v, cos_t)
    term2 = vec_mul(k_cross_v, sin_t)
    term3 = vec_mul(k, k_dot_v * (1 - cos_t))
    
    return vec_add(vec_add(term1, term2), term3)

def get_pixel_coords(hand_data, idx, w, h):
    lm = hand_data.landmarks[idx]
    # Note: We scale Z by width (or average of w/h) to keep 3D aspect ratio reasonable
    return (lm.x * w, lm.y * h, lm.z * w)

# --------------------------------------------------------
# MAIN LOGIC
# --------------------------------------------------------

def build_and_draw_tilted_plane(frame, hand_data, tilt_angle_deg=-25):
    """
    1. Defines a 'Base Plane' using Wrist(0), Index(5), Pinky(17).
    2. Defines an 'Axis' line from Index(5) to Pinky(17).
    3. Rotates the Base Normal around this Axis by `tilt_angle_deg`.
    4. Returns the Pivot Point (Index 5) and the new Rotated Normal.
    """
    h, w, _ = frame.shape
    
    # 1. Get Landmarks (Pixel Space)
    p0 = get_pixel_coords(hand_data, 0, w, h)   # Wrist
    p5 = get_pixel_coords(hand_data, 5, w, h)   # Index MCP (Pivot 1)
    p17 = get_pixel_coords(hand_data, 17, w, h) # Pinky MCP (Pivot 2)
    
    # 2. Define Base Plane vectors
    v_0_to_5 = vec_sub(p5, p0)
    v_0_to_17 = vec_sub(p17, p0)
    
    # Base Normal (perpendicular to flat palm)
    # Order 5->0 and 5->17 to ensure consistent direction
    base_normal = normalize(cross(vec_sub(p0, p5), vec_sub(p17, p5)))
    
    # 3. Define Rotation Axis (The Knuckle Line: 5 -> 17)
    rotation_axis = normalize(vec_sub(p17, p5))
    
    # 4. Apply Rotation (Rodrigues Formula)
    # Rotating the normal changes the 'angle' of the plane detection
    rotated_normal = rodrigues_rotation(base_normal, rotation_axis, tilt_angle_deg)
    
    # ----------------------------------------------------
    # DRAWING DEBUG INFO
    # ----------------------------------------------------
    pt5_2d = (int(p5[0]), int(p5[1]))
    pt17_2d = (int(p17[0]), int(p17[1]))
    
    # Draw the Hinge Axis (Blue)
    cv2.line(frame, pt5_2d, pt17_2d, (255, 200, 0), 2)
    
    # Draw the Normal Vector (Yellow)
    # We draw it starting from the middle of the knuckles
    mid_knuckle = vec_mul(vec_add(p5, p17), 0.5)
    mid_2d = (int(mid_knuckle[0]), int(mid_knuckle[1]))
    
    scale = 60
    end_point = vec_add(mid_knuckle, vec_mul(rotated_normal, scale))
    end_2d = (int(end_point[0]), int(end_point[1]))
    
    cv2.arrowedLine(frame, mid_2d, end_2d, (0, 255, 255), 2, tipLength=0.2)
    cv2.putText(frame, f"Angle: {tilt_angle_deg}", (mid_2d[0], mid_2d[1]-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    # Return pivot (p5) and direction (rotated_normal)
    return p5, rotated_normal

def annotate_fingertip_plane_status(frame, hand_data, plane_point, plane_normal):
    """
    Checks fingertip positions against the rotated plane.
    """
    h, w, _ = frame.shape
    
    # Index, Middle, Ring, Pinky Tips
    fingertips = [8, 12, 16, 20] 
    
    for tip_idx in fingertips:
        tip_pt = get_pixel_coords(hand_data, tip_idx, w, h)
        
        # Calculate distance to plane
        # Vector from Pivot (p5) to Tip
        vec_to_tip = vec_sub(tip_pt, plane_point)
        
        # Dot product with normal = distance from plane
        dist = dot(vec_to_tip, plane_normal)
        
        # Determine State
        # You may need to flip logic depending on rotation direction, 
        # but usually +dot means "in direction of normal" (Extended)
        # and -dot means "opposite to normal" (Closed).
        
        threshold = -5.0 # Small buffer
        
        tip_2d = (int(tip_pt[0]), int(tip_pt[1]))

        if dist > threshold:
            state = "EXTENDED"
            color = (0, 255, 0) # Green
        else:
            state = "CLOSED"
            color = (0, 0, 255) # Red
            
        cv2.circle(frame, tip_2d, 6, color, -1)
        cv2.putText(frame, state, (tip_2d[0]+10, tip_2d[1]), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

# Compatibility wrappers if needed
def draw_debug_reference_plane(frame, hand_data):
    # Just forwards to the tilted version with 0 angle for backward compat
    return build_and_draw_tilted_plane(frame, hand_data, tilt_angle_deg=0)

def point_above_plane(p, plane_pt, plane_normal):
    # Returns 1 if above, -1 if below
    v = vec_sub(p, plane_pt)
    d = dot(v, plane_normal)
    return 1 if d > 0 else -1