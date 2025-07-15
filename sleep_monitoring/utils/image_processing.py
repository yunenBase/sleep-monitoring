import cv2
import numpy as np
import time

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

def process_image_for_upload(frame_resized, tracked_boxes, tracked_objects, detection_duration, frame_width, frame_height, camera_id=None):
    """
    Proses gambar sebelum diunggah ke Cloudinary dengan opsi kustomisasi.
    """
    # Buat salinan gambar untuk diproses
    processed_image = frame_resized.copy()

    # Tambahkan bounding box hijau untuk objek dengan durasi >= detection_duration (tanpa teks)
    for obj_id, obj_data in tracked_boxes.items():
        if obj_id in tracked_objects and tracked_objects[obj_id]['total_duration'] >= detection_duration:
            x1, y1, x2, y2 = [int(coord) for coord in obj_data['box']]
            cv2.rectangle(processed_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            print(f"Menambahkan bounding box hijau untuk ID {obj_id} dengan durasi {tracked_objects[obj_id]['total_duration']}")

    # Tambahkan kustomisasi opsional di sini
    if camera_id is not None:
        cv2.putText(processed_image, f"Camera ID: {camera_id}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.putText(processed_image, f"Processed at {time.strftime('%H:%M:%S')}", 
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    return processed_image