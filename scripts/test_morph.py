import cv2
import numpy as np

# Create a synthetic image of the track (480x640)
# Dark tape on light floor -> thresholded mask will be white tape on black bg
mask = np.zeros((192, 640), dtype=np.uint8)

# Draw parallel lines (diagonal towards center)
cv2.line(mask, (100, 192), (250, 0), 255, 30) # Left line
cv2.line(mask, (540, 192), (390, 0), 255, 30) # Right line

# Draw horizontal branches
# Left branch protruding left
cv2.rectangle(mask, (60, 100), (160, 120), 255, -1)
# Right branch protruding right
cv2.rectangle(mask, (480, 100), (580, 120), 255, -1)

# Save the synthetic original
cv2.imwrite("synthetic_original.png", mask)

# Strategy 1: Horizontal Opening
kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (45, 1))
opened_h = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_h)
cv2.imwrite("synthetic_opened_h.png", opened_h)

# Find contours in the opened image
contours, _ = cv2.findContours(opened_h, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"Found {len(contours)} horizontal objects")
for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    print(f"Object: x={x}, y={y}, w={w}, h={h}, area={cv2.contourArea(c)}")
