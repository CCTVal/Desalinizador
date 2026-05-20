import numpy as np
import cv2
from collections import Counter

# Load the image
image_path = "DSC_0111.JPG"
image = cv2.imread(image_path)

# Constants

yellow_color = (0, 255, 255) # BGR for yellow
red_color = (0, 0, 255)     # BGR for red
lens = "Tamron" # lens = "Sigma"
# (0 is pure black, 255 is pure white)
black_threshold = (16 if lens == "Sigma" else 27) * 2.55 # Pixels darker than this are considered "core black"
border_darkness_threshold = (22 if lens == "Sigma" else 36) * 2.55 # Pixels darker than this are considered "border black"

if image is None:
    print(f"Error: Could not load image from {image_path}")
else:
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to smooth the image and handle diffuse circles
    # Kernel size 7x7 and sigmaX 0 are common starting points
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # Threshold for the overall circle (border)
    # cv2.THRESH_BINARY_INV means pixels <= thresh become 255 (white), else 0 (black).
    # This makes dark regions stand out as white blobs for contour detection.
    _, border_thresh = cv2.threshold(blurred, border_darkness_threshold, 255, cv2.THRESH_BINARY_INV)

    # Threshold for the core of the circle (stricter blackness)
    _, core_thresh = cv2.threshold(blurred, black_threshold, 255, cv2.THRESH_BINARY_INV)

    # Find contours on the border thresholded image
    # cv2.RETR_EXTERNAL retrieves only the extreme outer contours
    # cv2.CHAIN_APPROX_SIMPLE compresses horizontal, vertical, and diagonal segments
    contours, _ = cv2.findContours(core_thresh.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    detected_circles_info = []
    output_image = image.copy() # Image to draw boxes with data
    debug_image = image.copy() # Image to paint the waterdrops

    print(f"Found {len(contours)} initial contours.")

    for i, contour in enumerate(contours):
        # Calculate area
        area = cv2.contourArea(contour)

        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)

        # --- Filtering Contours ---
        # 1. Area filter: Remove very small (noise) or very large (entire image, non-circle) contours.
        #    These values might need tuning.
        min_area = 5
        max_area = 1000
        if not (min_area < area < max_area):
            print(f"  Contour {i+1} rejected (Area: {area:.0f}).")
            continue

        # 2. Aspect ratio filter: Check if the bounding box is roughly square/circular.
        aspect_ratio = float(w) / h
        # A perfect circle has an aspect ratio of 1. Allow some deviation for diffuse circles.
        if not (0.5 < aspect_ratio < 5.0):
            print(f"  Contour {i+1} rejected (Aspect Ratio: {aspect_ratio:.2f}).")
            continue

        
        # 3. Circularity filter: A more robust measure. Perfect circle has circularity of 1.
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            # print(f"  Contour {i+1} rejected (Perimeter is zero).")
            continue
        circularity = (4 * np.pi * area) / (perimeter * perimeter)
        # A lower bound for circularity (e.g., > 0.4) to consider it circle-like.
        if circularity < 0.8:
            # print(f"  Contour {i+1} rejected (Circularity: {circularity:.2f}).")
            continue
        
        # --- Core Check (using the stricter black_threshold) ---
        # Create a mask for the current contour
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1) # Draw contour as filled white on black mask

        # Apply the core threshold image to the mask, to count pixels darker than `black_threshold`
        # that are *inside* the current contour.
        masked_core_pixels = cv2.bitwise_and(core_thresh, mask)
        core_pixel_count = cv2.countNonZero(masked_core_pixels)

        # 4. Core Ratio filter: If a significant portion of the contour is identified as "core",
        #    then it's a valid black circle. Define a ratio, e.g., at least 20% of the contour's
        #    area should be "core" pixels.
        core_ratio = core_pixel_count / area
        if core_ratio < 0.9: # Adjust this ratio based on how "solid" the core should be
            # print(f"  Contour {i+1} rejected (Core Ratio: {core_ratio:.2f}).")
            continue
        
        # If all checks pass, consider it a valid diffuse black circle
        detected_circles_info.append({
            "pixel_count": area,
            "max_width": w,
            "max_height": h,
            "bounding_box": (x, y, w, h) # Storing for drawing purposes if needed
        })

        # --- Visualization for selected spots ---
        core = np.logical_and(core_thresh == 255, masked_core_pixels == 255)
        debug_image[core] = red_color
        # Wanted to paint both the core pixel and the gray pixels, but I still don't know why does it not work.
        #border = np.logical_and(border_thresh == 255, mask == 255)
        #debug_image[border] = yellow_color
        
        # --- End visualization for selected spots


        # Draw bounding box and circle properties on the output image for visualization
        cv2.rectangle(output_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(output_image, f"Area: {area:.0f}", (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(output_image, f"W: {w}, H: {h}", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    if detected_circles_info:
        print("\nDetected Diffuse Black Circles:")
        print(len(detected_circles_info))
        '''
        for i, circle in enumerate(detected_circles_info):
            print(f"Circle {i+1}:")
            print(f"  Pixel Count: {circle['pixel_count']:.0f}")
            print(f"  Maximum Width: {circle['max_width']}")
            print(f"  Maximum Height: {circle['max_height']}")
            print("-" * 20)
        '''

        # Display the image with detected circles for verification
        print("Generating images with detected circles:")
        cv2.imwrite(image_path + "_new.jpg", output_image)
        cv2.imwrite(image_path + "_debug.jpg", debug_image)

        # Extract all max_width values
        max_widths = [circle['max_width'] for circle in detected_circles_info]

        # Calculate frequency of each max_width
        width_counts = Counter(max_widths)

        # Calculate mean and standard deviation
        mean_width = np.mean(max_widths)
        std_dev_width = np.std(max_widths)
        print(f"Mean of Max Widths: {mean_width:.2f} pixels")
        print(f"Standard Deviation of Max Widths: {std_dev_width:.2f} pixels")

    else:
        print("No diffuse black circles detected with the current thresholds and filters.")

