"""
Image Preprocessing Utilities for Document OCR on Snapdragon X / Hexagon NPU.
Provides:
- Grayscale conversion & CLAHE contrast normalization.
- Robust skew detection and deskewing via contour minimum area bounding.
- Text line segmentation for full document transcription.
- Tensor preparation formatted for TrOCR ONNX inference (CHW float32).
"""

import cv2
import numpy as np
from typing import List, Tuple


def detect_and_correct_skew(gray: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Detects document skew angle and rotates the image back to level horizontal orientation.
    Returns:
        tuple of (deskewed_gray_image, detected_angle_degrees)
    """
    # Invert binary threshold to isolate text pixels
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Extract coordinates of all non-zero foreground (text) pixels
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 50:
        return gray, 0.0

    # Determine minimum area bounding rectangle
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # Normalize OpenCV angle convention (-90 to 0 or 0 to 90 depending on version)
    if angle < -45.0:
        angle = -(90.0 + angle)
    elif angle > 45.0:
        angle = 90.0 - angle
    else:
        angle = -angle

    # Filter out negligible tilt (< 0.25 degrees) or extreme invalid bounds
    if abs(angle) < 0.25 or abs(angle) > 45.0:
        return gray, 0.0

    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(
        gray,
        rot_mat,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,  # White border fill for clean document background
    )

    return deskewed, angle


def normalize_contrast(gray: np.ndarray) -> np.ndarray:
    """
    Enhances local document contrast using Contrast Limited Adaptive Histogram
    Equalization (CLAHE). Effectively removes uneven lighting and scanner shadows.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def preprocess_document_image(image_path: str) -> Tuple[np.ndarray, float]:
    """
    Loads document image from disk and executes the primary preprocessing pipeline:
    1. Grayscale conversion.
    2. Document deskewing.
    3. CLAHE contrast normalization.

    Returns:
        (preprocessed_image_gray, skew_angle_corrected)
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image from '{image_path}'. Ensure the path is valid.")

    if len(img.shape) == 3 and img.shape[2] == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    deskewed, angle = detect_and_correct_skew(gray)
    normalized = normalize_contrast(deskewed)

    return normalized, angle


def segment_text_lines(gray: np.ndarray) -> List[np.ndarray]:
    """
    Segments multi-line documents into individual text line crops using
    morphological horizontal dilation and contour analysis.
    Filters out document boundaries/tables to cleanly isolate text lines.
    """
    h, w = gray.shape[:2]

    # Binarize with Otsu
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Create horizontal structuring element to connect words along each line
    kernel_w = max(20, w // 35)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=2)

    # Use RETR_LIST so text inside outer borders/frames is captured
    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    bounding_boxes = []
    min_line_height = max(8, h // 80)
    min_line_width = max(25, w // 25)

    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        # Skip contours that are whole-document borders or giant frames
        if bw >= 0.92 * w and bh >= 0.75 * h:
            continue
        # Skip purely vertical borders / separator lines
        if bh > 4 * bw and bw < 10:
            continue
        # Valid text line bounding box
        if min_line_height <= bh <= int(0.35 * h) and bw >= min_line_width:
            bounding_boxes.append((x, y, bw, bh))

    if not bounding_boxes:
        return [gray]

    # Sort lines top-to-bottom by y-coordinate
    bounding_boxes.sort(key=lambda b: b[1])

    # Filter out overlapping/duplicate boxes vertically (Non-Max Suppression on Y)
    filtered_boxes = []
    for b in bounding_boxes:
        x, y, bw, bh = b
        overlap = False
        for fb in filtered_boxes:
            fx, fy, fbw, fbh = fb
            # If two boxes overlap vertically by more than 50% of the smaller one and horizontally overlap
            y_overlap = max(0, min(y + bh, fy + fbh) - max(y, fy))
            if y_overlap > 0.5 * min(bh, fbh):
                overlap = True
                break
        if not overlap:
            filtered_boxes.append(b)

    # Sort again top-to-bottom
    filtered_boxes.sort(key=lambda b: b[1])

    line_crops = []
    pad = 4
    for x, y, bw, bh in filtered_boxes:
        y1 = max(0, y - pad)
        y2 = min(h, y + bh + pad)
        x1 = max(0, x - pad)
        x2 = min(w, x + bw + pad)
        crop = gray[y1:y2, x1:x2]
        if crop.size > 0:
            line_crops.append(crop)

    return line_crops if line_crops else [gray]


def prepare_trocr_tensor(
    img_gray_or_bgr: np.ndarray,
    target_size: Tuple[int, int] = (384, 384)
) -> np.ndarray:
    """
    Converts preprocessed document image or line crop into a standardized
    CHW float32 tensor in range [0.0, 1.0] for Qualcomm AI Hub TrOCR ONNX inference.
    (Qualcomm's model graph handles internal normalization).
    """
    # Convert single channel grayscale to 3-channel RGB
    if len(img_gray_or_bgr.shape) == 2:
        rgb = cv2.cvtColor(img_gray_or_bgr, cv2.COLOR_GRAY2RGB)
    elif img_gray_or_bgr.shape[2] == 3:
        rgb = cv2.cvtColor(img_gray_or_bgr, cv2.COLOR_BGR2RGB)
    else:
        rgb = img_gray_or_bgr

    # Resize to TrOCR input resolution (384x384)
    resized = cv2.resize(rgb, target_size, interpolation=cv2.INTER_LANCZOS4)

    # Scale to [0.0, 1.0] float32 as required by Qualcomm AI Hub TrOCR spec
    normalized = resized.astype(np.float32) / 255.0

    # Transpose HWC -> CHW and add batch dimension -> NCHW (1, 3, H, W)
    chw = np.transpose(normalized, (2, 0, 1))
    tensor = np.expand_dims(chw, axis=0)

    return tensor

