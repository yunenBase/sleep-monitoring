import sys
import cv2
import time
import os
import shutil  # Untuk menghapus file sementara jika perlu
from yoloDet import YoloTRT
from config.config import DETECTION_DURATION, DETECTION_DURATION_CONTINUE
from utils.image_processing import add_padding, remove_padding, adjust_bboxes
from utils.tracking import update_tracks
from utils.cloud_storage import upload_to_cloudinary
from database.firestore_db import save_to_firestore_detection, save_to_firestore_duration
from notifications.telegram import send_to_telegram, send_to_telegram_new
from datetime import datetime
import pytz

# Inisialisasi zona waktu Indonesia (WIB, UTC+7)
tz_indonesia = pytz.timezone('Asia/Jakarta')

# Inisialisasi model YOLO
model = YoloTRT(
    library="yolov5/build/libmyplugins.so",
    engine="models/newhyp.engine",
    conf=0.5,
    yolo_ver="v5"
)

# Inisialisasi video capture
# cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap = cv2.VideoCapture('videos/camlamakanan.mp4')
if not cap.isOpened():
    print("Error: Tidak dapat membuka video tes-vid.mp4")
    sys.exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# --- Blok Kode Baru: Membuat folder untuk menyimpan gambar ---
capture_dir = 'capture'
if not os.path.exists(capture_dir):
    os.makedirs(capture_dir)
    print(f"Direktori '{capture_dir}' berhasil dibuat.")
# -----------------------------------------------------------

frame_count = 0
capture_count = 0  # Variabel untuk penamaan file gambar
tracked_objects = {}  # {id: {'start_time': float, 'total_duration': float, 'last_notification_time': float, 'notified_first': bool, 'notified_second': bool, 'detection_time': float}}
tracked_boxes = {}    # {id: {'centroid': tuple, 'box': list, 'class': str, 'conf': float}}
next_id = 0
camera_id = 2  # Identitas kamera

# Main loop
while True:
    ret, frame = cap.read()  # 'frame' adalah gambar asli
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
        print(f"  Deteksi {idx} (sebelum filter): Kelas={obj['class']}, Conf={obj['conf']}, Box={obj['box']}")

    # Filter hanya objek "sleep"
    detections = [obj for obj in detections if obj['class'] == "sleep"]
    print(f"Deteksi 'sleep': {len(detections)} objek")

    # Debugging koordinat sebelum dan sesudah adjust_bboxes
    for idx, obj in enumerate(detections):
        print(f"  Deteksi {idx} (sebelum adjust_bboxes): Kelas={obj['class']}, Conf={obj['conf']}, Box={obj['box']}")
    detections = adjust_bboxes(detections, padding)
    for idx, obj in enumerate(detections):
        print(f"  Deteksi {idx} (sesudah adjust_bboxes): Kelas={obj['class']}, Conf={obj['conf']}, Box={obj['box']}")

    tracked_boxes, next_id = update_tracks(tracked_boxes, detections, camera_id)
    current_time = time.time()

    # Inisialisasi objek baru dengan total_duration dan status notifikasi
    for obj_id, obj_data in list(tracked_boxes.items()):  # Use list() to create a copy
        if obj_id not in tracked_objects:
            unique_obj_id = f"{camera_id}_{int(current_time)}"
            tracked_objects[unique_obj_id] = {
                'start_time': current_time,
                'total_duration': 0.0,
                'last_notification_time': 0.0,
                'notified_first': False,  # Flag untuk notifikasi pertama
                'notified_second': False,  # Flag untuk notifikasi kedua
                'detection_time': 0.0      # Inisialisasi dengan 0, akan diperbarui saat notifikasi pertama
            }
            print(f"Deteksi baru untuk ID {unique_obj_id}")
            tracked_boxes[unique_obj_id] = tracked_boxes.pop(obj_id)

    # Buat frame untuk upload tanpa bounding box awal
    frame_for_upload = frame_resized.copy()

    # Update durasi dan cek notifikasi
    for obj_id in list(tracked_objects.keys()):
        if obj_id in tracked_boxes:
            duration = current_time - tracked_objects[obj_id]['start_time']
            tracked_objects[obj_id]['total_duration'] = duration
            print(f"ID {obj_id}: Durasi deteksi = {duration:.2f} detik, Total Duration = {tracked_objects[obj_id]['total_duration']:.2f} detik, Notified First = {tracked_objects[obj_id]['notified_first']}, Notified Second = {tracked_objects[obj_id]['notified_second']}")
            
            # Notifikasi pertama saat melebihi DETECTION_DURATION
            if tracked_objects[obj_id]['total_duration'] >= DETECTION_DURATION and not tracked_objects[obj_id]['notified_first']:
                if tracked_objects[obj_id]['detection_time'] == 0.0:  # Set detection_time saat notifikasi pertama
                    tracked_objects[obj_id]['detection_time'] = current_time
                valid_objects = [oid for oid in tracked_objects.keys() if tracked_objects[oid]['total_duration'] >= DETECTION_DURATION]
                sleep_count = len(valid_objects)
                
                # Tambahkan bounding box hijau untuk notifikasi pertama
                temp_frame = frame_for_upload.copy()
                x1, y1, x2, y2 = [int(coord) for coord in tracked_boxes[obj_id]['box']]
                cv2.rectangle(temp_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Hijau
                label = obj_id
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                label_x = x1
                label_y = y1 - 10 if y1 - 10 > 10 else y1 + label_size[1] + 10
                cv2.rectangle(temp_frame, (label_x, label_y - label_size[1] - 4), (label_x + label_size[0] + 4, label_y + 4), (0, 255, 0), cv2.FILLED)
                cv2.putText(temp_frame, label, (label_x + 2, label_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                # Proses dan unggah notifikasi pertama
                temp_image_path = os.path.join(capture_dir, f'temp_{obj_id}_{time.strftime("%H-%M-%S")}.jpg')
                cv2.imwrite(temp_image_path, temp_frame)
                print(f"Gambar sementara disimpan di: {temp_image_path}")

                img = cv2.imread(temp_image_path)
                if img is None:
                    print(f"Error: Gagal membaca gambar dari {temp_image_path}")
                    continue
                processed_image_path = os.path.join(capture_dir, f'processed_{obj_id}_{time.strftime("%H-%M-%S")}.jpg')
                cv2.imwrite(processed_image_path, img)
                print(f"Gambar diproses dan disimpan di: {processed_image_path}")

                image_url = upload_to_cloudinary(img)
                if image_url:
                    print(f"Objek {obj_id} dengan durasi {tracked_objects[obj_id]['total_duration']} detik diunggah (notifikasi pertama)")
                    timestamp = time.time()
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
                    # Konversi timestamp ke WIB
                    detection_start_time_wib = datetime.fromtimestamp(tracked_objects[obj_id]['start_time'], tz=tz_indonesia).strftime('%d-%m-%Y %H:%M:%S WIB')
                    detection_time_wib = datetime.fromtimestamp(tracked_objects[obj_id]['detection_time'], tz=tz_indonesia).strftime('%d-%m-%Y %H:%M:%S WIB')
                    send_time_wib = datetime.fromtimestamp(timestamp, tz=tz_indonesia).strftime('%d-%m-%Y %H:%M:%S WIB')
                    caption = f"Ada yang ketiduran nih | Deteksi Awal: {detection_start_time_wib}, Deteksi: {detection_time_wib}, Pengiriman: {send_time_wib}, Duration: {tracked_objects[obj_id]['total_duration']:.2f} seconds"
                    send_to_telegram(image_url, caption, tracked_objects[obj_id]['total_duration'])
                    tracked_objects[obj_id]['notified_first'] = True
                    tracked_objects[obj_id]['last_notification_time'] = timestamp
                    delay = (timestamp - tracked_objects[obj_id]['detection_time']) * 1000  # Konversi ke milidetik
                    print(f"Delay deteksi ke pengiriman untuk ID {obj_id}: {delay:.2f} ms")

                os.remove(temp_image_path)
                os.remove(processed_image_path)

            # Notifikasi kedua saat melebihi DETECTION_DURATION_CONTINUE
            if tracked_objects[obj_id]['total_duration'] >= DETECTION_DURATION_CONTINUE and not tracked_objects[obj_id]['notified_second']:
                valid_objects = [oid for oid in tracked_objects.keys() if tracked_objects[oid]['total_duration'] >= DETECTION_DURATION_CONTINUE]
                sleep_count = len(valid_objects)
                
                # Tambahkan bounding box oranye untuk notifikasi kedua
                temp_frame = frame_for_upload.copy()
                x1, y1, x2, y2 = [int(coord) for coord in tracked_boxes[obj_id]['box']]
                cv2.rectangle(temp_frame, (x1, y1), (x2, y2), (0, 165, 255), 2)  # Oranye
                label = obj_id
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                label_x = x1
                label_y = y1 - 10 if y1 - 10 > 10 else y1 + label_size[1] + 10
                cv2.rectangle(temp_frame, (label_x, label_y - label_size[1] - 4), (label_x + label_size[0] + 4, label_y + 4), (0, 165, 255), cv2.FILLED)
                cv2.putText(temp_frame, label, (label_x + 2, label_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                # Proses dan unggah notifikasi kedua
                temp_image_path = os.path.join(capture_dir, f'temp_{obj_id}_{time.strftime("%H-%M-%S")}.jpg')
                cv2.imwrite(temp_image_path, temp_frame)
                print(f"Gambar sementara disimpan di: {temp_image_path}")

                img = cv2.imread(temp_image_path)
                if img is None:
                    print(f"Error: Gagal membaca gambar dari {temp_image_path}")
                    continue
                processed_image_path = os.path.join(capture_dir, f'processed_{obj_id}_{time.strftime("%H-%M-%S")}.jpg')
                cv2.imwrite(processed_image_path, img)
                print(f"Gambar diproses dan disimpan di: {processed_image_path}")

                image_url = upload_to_cloudinary(img)
                if image_url:
                    print(f"Objek {obj_id} dengan durasi {tracked_objects[obj_id]['total_duration']} detik diunggah (notifikasi kedua)")
                    timestamp = time.time()
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
                    # Konversi timestamp ke WIB
                    detection_start_time_wib = datetime.fromtimestamp(tracked_objects[obj_id]['start_time'], tz=tz_indonesia).strftime('%d-%m-%Y %H:%M:%S WIB')
                    detection_time_wib = datetime.fromtimestamp(tracked_objects[obj_id]['detection_time'], tz=tz_indonesia).strftime('%d-%m-%Y %H:%M:%S WIB')
                    send_time_wib = datetime.fromtimestamp(timestamp, tz=tz_indonesia).strftime('%d-%m-%Y %H:%M:%S WIB')
                    caption = f"Terpantau masih tidur ya | Deteksi Awal: {detection_start_time_wib}, Deteksi: {detection_time_wib}, Pengiriman: {send_time_wib}, Duration: {tracked_objects[obj_id]['total_duration']:.2f} seconds"
                    send_to_telegram_new(image_url, caption, tracked_objects[obj_id]['total_duration'])
                    tracked_objects[obj_id]['notified_second'] = True
                    tracked_objects[obj_id]['last_notification_time'] = timestamp
                    delay = (timestamp - tracked_objects[obj_id]['detection_time']) * 1000  # Konversi ke milidetik
                    print(f"Delay deteksi ke pengiriman untuk ID {obj_id}: {delay:.2f} ms")

                os.remove(temp_image_path)
                os.remove(processed_image_path)
        else:
            start_timestamp = tracked_objects[obj_id]['start_time']
            end_timestamp = current_time
            if tracked_objects[obj_id]['total_duration'] > 0:
                save_to_firestore_duration(start_timestamp, end_timestamp, obj_id, camera_id=camera_id)
            print(f"Deteksi terhenti untuk ID {obj_id}, Total Duration: {tracked_objects[obj_id]['total_duration']:.2f} detik")
            del tracked_objects[obj_id]

    # Tampilkan frame untuk inferensi dengan bounding box tetap hijau
    frame_display = frame_resized.copy()
    for obj_id, obj_data in tracked_boxes.items():
        if obj_id in tracked_objects:
            x1, y1, x2, y2 = [int(coord) for coord in obj_data['box']]
            cv2.rectangle(frame_display, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Tetap hijau
            cv2.putText(frame_display, f"ID: {obj_id}, Duration: {tracked_objects[obj_id]['total_duration']:.2f}s", 
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    fps_text = "FPS: {:.2f}".format(1 / t)
    cv2.putText(frame_display, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Output", frame_display)

    key = cv2.waitKey(1) & 0xFF

    # --- Blok Kode Baru: Logika untuk menangkap gambar ---
    if key == ord('c'):
        capture_count += 1
        image_name = os.path.join(capture_dir, f'capture_{capture_count}.png')
        cv2.imwrite(image_name, frame)
        print(f"Gambar berhasil disimpan sebagai {image_name}")
    # ----------------------------------------------------

    elif key == ord('q'):
        for obj_id in tracked_objects:
            start_timestamp = tracked_objects[obj_id]['start_time']
            end_timestamp = time.time()
            if tracked_objects[obj_id]['total_duration'] > 0:
                save_to_firestore_duration(start_timestamp, end_timestamp, obj_id, camera_id=camera_id)
                print(f"Program berhenti, ID {obj_id} Total Duration: {tracked_objects[obj_id]['total_duration']:.2f} detik")
        break

cap.release()
cv2.destroyAllWindows()
