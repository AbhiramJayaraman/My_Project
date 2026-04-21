import numpy as np
import cv2
from config import IMG_WIDTH,IMG_HEIGHT,GRID_WIDTH_CM,GRID_HEIGHT_CM,MARGIN_TOP,MARGIN_RIGHT,CM_TO_PX

#need to add the constants as in configuration.location.MARGIn...

def create_map_background(scale=0.5, path="final_grid_map.png"):
    """
    Loads the annotated map image with grid and axes, scaled down.

    Args:
        scale (float): Scale factor to resize image.
        path (str): Path to grid image file.

    Returns:
        map_img (np.ndarray): Scaled map image
        scale (float): The used scale factor
    """
    map_img = cv2.imread(path)
    if map_img is None:
        raise FileNotFoundError(f"Map image not found at {path}")
    if scale != 1.0:
        map_img = cv2.resize(map_img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return map_img, scale

def draw_map_view(map_img, position_cm, label_name, colour,scale=0.5):
    """
    Plots a labeled point in cm onto the map image.

    Args:
        map_img (np.ndarray): Scaled map image to draw on
        position_cm (tuple): (x_cm, y_cm) position in cm
        label_name (str): Text label for this point
        scale (float): The scale used when loading the map

    Returns:
        map_img (np.ndarray): Modified image with dot and label
    """
    x_cm, y_cm = position_cm

    # Compute full-resolution pixel position
    origin_x_full = IMG_WIDTH - GRID_WIDTH_CM - MARGIN_RIGHT
    origin_y_full = MARGIN_TOP
    x_px_full = origin_x_full + (GRID_WIDTH_CM - x_cm)
    y_px_full = origin_y_full + y_cm

    # Scale to match map
    px = int(x_px_full * scale)
    py = int(y_px_full * scale)
   

    # Draw the point and label
    cv2.circle(map_img, (px, py), 5, colour, -1)
    label_text = f"{label_name} ({int(x_cm)}cm, {int(y_cm)}cm)"
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4
    thickness = 1
    text_size, _ = cv2.getTextSize(label_text, font, font_scale, thickness)
    text_width = text_size[0]
    max_width = map_img.shape[1] - px - 10
    if text_width > max_width:
        # Wrap into 2 lines
        label_main = label_name
        label_coords = f"({int(x_cm)}cm, {int(y_cm)}cm)"
        cv2.putText(map_img, label_main, (px, max(15, py - 15)), font, font_scale, (0, 0, 255), thickness)
        cv2.putText(map_img, label_coords, (px, py - 2), font, font_scale, (0, 0, 255), thickness)
    else:
        text_x = max(0, px - 40)
        text_y = max(15, py - 10)
        cv2.putText(map_img, label_text, (text_x, text_y), font, font_scale, (0, 0, 255), thickness)
    return map_img
    
    
    # === MAIN ===
if __name__ == "__main__":
	map_img, scalemap = create_map_background(scale=0.5)
	cv2.imshow("Testing map creation",map_img)
	
	#testing the draw function
	position = (120.0,200.0)
	label = "test"
	draw_map_view(map_img, position, label, scalemap)
	cv2.imshow("Testing map creation",map_img)
	cv2.waitKey(0)
	cv2.destroyAllWindows()