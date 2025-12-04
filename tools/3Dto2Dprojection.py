import numpy as np
import cv2

# Define the camera matrix
fx = 800
fy = 800
cx = 640
cy = 480
camera_matrix = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], np.float32)

# Define the distortion coefficients
dist_coeffs = np.zeros((5, 1), np.float32)

# Define the 3D point in the world coordinate system
x, y, z = 10, 10, 10
points_3d = np.array([[[x, y, z]]], np.float32)

# Define the rotation and translation vectors
rvec = np.zeros((3, 1), np.float32)
tvec = np.zeros((3, 1), np.float32)

# Map the 3D point to 2D point
points_2d, _ = cv2.projectPoints(points_3d, rvec, tvec, camera_matrix, dist_coeffs)

# Display the 2D point
print("2D Point:", points_2d)
