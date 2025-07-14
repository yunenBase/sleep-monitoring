import cv2

def add_padding(image, target_size=(640, 640)):
    h, w = image.shape[:2]
    target_w, target_h = target_size
    
    pad_top = (target_h - h) // 2
    pad_bottom = target_h - h - pad_top
    pad_left = (target_w - w) // 2
    pad_right = target_w - w - pad_left
    
    padded_image = cv2.copyMakeBorder(
        image,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_CONSTANT,
        value=(0, 0, 0)
    )
    
    return padded_image, (pad_top, pad_bottom, pad_left, pad_right)

def remove_padding(image, padding):
    pad_top, pad_bottom, pad_left, pad_right = padding
    h, w = image.shape[:2]
    cropped_image = image[pad_top:h-pad_bottom, pad_left:w-pad_right]
    return cropped_image

def adjust_bboxes(detections, padding):
    pad_top, _, pad_left, _ = padding
    adjusted_detections = []
    for obj in detections:
        x1, y1, x2, y2 = obj['box']
        x1_adj = x1 - pad_left
        x2_adj = x2 - pad_left
        y1_adj = y1 - pad_top
        y2_adj = y2 - pad_top
        adjusted_detections.append({
            'class': obj['class'],
            'conf': obj['conf'],
            'box': [x1_adj, y1_adj, x2_adj, y2_adj]
        })
    return adjusted_detections