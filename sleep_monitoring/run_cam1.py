import sys
import cv2
import time
from yoloDet import YoloTRT
from config.config import DETECTION_DURATION
from utils.image_processing import add_padding, remove_padding, adjust_bboxes
from utils.tracking import update_tracks
from utils.cloud_storage import upload_to_cloudinary
from database.firestore_db import save_to_firestore_detection, save_to_firestore_duration
from notifications.telegram import send_to_telegram

# Inisialisasi model YOLO
model = YoloTRT(
    library="yolov5/build/libmyplugins.so",
    engine="yolov5/build/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

# Inisialisasi video capture
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
# cap = cv2.VideoCapture('videos/camlamakiri.mp4')
if not cap.isOpened():
    print("Error: Tidak dapat membuka video tes-vid.mp4")
    sys.exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

frame_count = 0
tracked_objects = {}  # {id: {'start_time': float, 'message_sent': bool, 'total_duration': float}}
tracked_boxes = {}    # {id: {'centroid': tuple, 'box': list, 'class': str, 'conf': float}}
next_id = 0
camera_id = 1  # Identitas kamera

# Main loop
while True:
    ret, frame = cap.read()
    if not ret:
        print("Gagal mengambil frame dari video")
        break

    frame_count += 1
    frame_resized = cv2.resize(frame, (640, 360))  # Frame resized untuk inferensi
    frame_height, frame_width = frame_resized.shape[:2]
    frame_for_inference, padding = add_padding(frame_resized, target_size=(640, 640))
    
    detections, t = model.Inference(frame_for_inference)
    print(f"Frame {frame_count}: {len(detections)} objek terdeteksi")
    for idx, obj in enumerate(detections):
        print(f"  Deteksi {idx}: Kelas={obj['class']}, Conf={obj['conf']}, Box={obj['box']}")

    detections = [obj for obj in detections if obj['class'] == "sleep"]
    print(f"Deteksi 'sleep': {len(detections)} objek")

    detections = adjust_bboxes(detections, padding)
    tracked_boxes, next_id = update_tracks(tracked_boxes, detections)
    current_time = time.time()

    # Inisialisasi objek baru dengan total_duration
    for obj_id, obj_data in tracked_boxes.items():
        if obj_id not in tracked_objects:
            tracked_objects[obj_id] = {
                'start_time': current_time,
                'message_sent': False,
                'total_duration': 0.0
            }
            print(f"Deteksi baru untuk ID {obj_id}")

    frame_for_upload = remove_padding(frame_for_inference, padding)

    # Update durasi dan cek notifikasi
    for obj_id in list(tracked_objects.keys()):
        if obj_id in tracked_boxes:
            duration = current_time - tracked_objects[obj_id]['start_time']
            tracked_objects[obj_id]['total_duration'] = duration
            print(f"ID {obj_id}: Durasi deteksi = {duration:.2f} detik, Total Duration = {tracked_objects[obj_id]['total_duration']:.2f} detik, Message Sent = {tracked_objects[obj_id]['message_sent']}")
            if not tracked_objects[obj_id]['message_sent'] and duration >= DETECTION_DURATION:
                image_url = upload_to_cloudinary(frame_for_upload)
                if image_url:
                    timestamp = time.time()
                    sleep_count = len(detections)
                    # Ambil koordinat relatif dari bounding box
                    box = tracked_boxes[obj_id]['box']
                    x1, y1, x2, y2 = [int(coord) for coord in box]
                    x1_rel = x1 / frame_width
                    y1_rel = y1 / frame_height
                    x2_rel = x2 / frame_width
                    y2_rel = y2 / frame_height
                    coords_rel = {
                        'x1': x1_rel,
                        'y1': y1_rel,
                        'x2': x2_rel,
                        'y2': y2_rel
                    }
                    save_to_firestore_detection(timestamp, image_url, sleep_count, obj_id, tracked_objects[obj_id]['total_duration'], coords_rel, camera_id=camera_id)
                    caption = f"Sleeping student detected (ID: {obj_id}, Count: {sleep_count}, Camera: {camera_id})"
                    send_to_telegram(image_url, caption, tracked_objects[obj_id]['total_duration'])
                    tracked_objects[obj_id]['message_sent'] = True
        else:
            # Simpan durasi ke koleksi duration saat deteksi berhenti
            start_timestamp = tracked_objects[obj_id]['start_time']
            end_timestamp = current_time
            if tracked_objects[obj_id]['total_duration'] > 0:
                save_to_firestore_duration(start_timestamp, end_timestamp, obj_id, camera_id=camera_id)
            print(f"Deteksi terhenti untuk ID {obj_id}, Total Duration: {tracked_objects[obj_id]['total_duration']:.2f} detik")
            del tracked_objects[obj_id]

    for obj_id, obj_data in tracked_boxes.items():
        x1, y1, x2, y2 = [int(coord) for coord in obj_data['box']]
        cv2.rectangle(frame_for_upload, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame_for_upload, f"ID: {obj_id}, Duration: {tracked_objects[obj_id]['total_duration']:.2f}s", 
                    (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    fps_text = "FPS: {:.2f}".format(1 / t)
    cv2.putText(frame_for_upload, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Output", frame_for_upload)

    if cv2.waitKey(1) == ord('q'):
        # Simpan durasi terakhir untuk semua objek yang masih terdeteksi saat loop berhenti
        for obj_id in tracked_objects:
            start_timestamp = tracked_objects[obj_id]['start_time']
            end_timestamp = time.time()
            if tracked_objects[obj_id]['total_duration'] > 0:
                save_to_firestore_duration(start_timestamp, end_timestamp, obj_id, camera_id=camera_id)
                print(f"Program berhenti, ID {obj_id} Total Duration: {tracked_objects[obj_id]['total_duration']:.2f} detik")
        break

cap.release()
cv2.destroyAllWindows()
