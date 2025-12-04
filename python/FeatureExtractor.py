import math


# ==========================================
# 1. MATH & GEOMETRY (Pure Functions)
# ==========================================
def vec_dist(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def compute_angle(a, b, c):
    """Calculates angle ABC (in degrees) at joint B."""
    # Vector BA
    v1 = (a.x - b.x, a.y - b.y, a.z - b.z)
    # Vector BC
    v2 = (c.x - b.x, c.y - b.y, c.z - b.z)

    dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
    mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2)
    mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2 + v2[2] ** 2)

    if mag1 * mag2 == 0:
        return 0.0
    cosine = dot / (mag1 * mag2)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))
