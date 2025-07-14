import sys
import cv2
import requests
import os
from yoloDet import YoloTRT
from datetime import datetime
import time
import numpy as np
from scipy.spatial import distance as dist
import cloudinary
import cloudinary.uploader
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import io

# Inisialisasi Cloudinary
cloudinary.config(
    cloud_name="doqvbpnf8",  # Ganti dengan cloud name dari dashboard Cloudinary
    api_key="541582174476865",
    api_secret="Z4puy0FmcUZR8lXdtJ-vfKB6NMY"  # Ganti dengan API secret dari dashboard Cloudinary
)

# Inisialisasi Firebase
cred = credentials.Certificate("sleepmonitoring-ed560-firebase-adminsdk-fbsvc-6a7f045e37.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Konfigurasi Telegram
TOKEN = "7744704117:AAFiwWyI7jpw3VcF013ae_T4CPUHLp1eDT4"
CHANNEL_ID = "-1002516589658"
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

# Fungsi untuk menghitung centroid bounding box
def get_centroid(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)

# Fungsi untuk memperbarui pelacakan objek
def update_tracks(objects, detections, max_distance=50):
    if len(objects) == 0:
        return {i: {'centroid': get_centroid(obj['box']), 'box': obj['box'], 'class': obj['class'], 'conf': obj['conf']}
                for i, obj in enumerate(detections)}, len(detections)
    
    object_centroids = np.array([obj['centroid'] for obj in objects.values()])
    detection_centroids = np.array([get_centroid(obj['box']) for obj in detections])
    
    if len(detection_centroids) == 0:
        return {}, len(objects)
    
    distances = dist.cdist(object_centroids, detection_centroids)
    rows = distances.min(axis=1).argsort()
    cols = distances.argmin(axis=1)[rows]
    
    used_rows, used_cols = set(), set()
    new_objects = {}
    next_id = max(objects.keys(), default=-1) + 1
    
    for row, col in zip(rows, cols):
        if row in used_rows or col in used_cols or distances[row, col] > max_distance:
            continue
        obj_id = list(objects.keys())[row]
        new_objects[obj_id] = {
            'centroid': detection_centroids[col],
            'box': detections[col]['box'],
            'class': detections[col]['class'],
            'conf': detections[col]['conf']
        }
        used_rows.add(row)
        used_cols.add(col)
    
    for col in range(len(detections)):
        if col not in used_cols:
            new_objects[next_id] = {
                'centroid': detection_centroids[col],
                'box': detections[col]['box'],
                'class': detections[col]['class'],
                'conf': detections[col]['conf']
            }
            next_id += 1
    
    return new_objects, next_id

# Fungsi untuk mengunggah gambar ke Cloudinary
def upload_to_cloudinary(image):
    try:
        # Pastikan gambar dalam format BGR, konversi ke RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Konversi ke PIL Image untuk pengkodean yang lebih andal
        pil_image = Image.fromarray(image_rgb)
        # Simpan ke buffer sebagai JPG
        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)
        # Unggah ke Cloudinary
        response = cloudinary.uploader.upload(
            buffer,
            upload_preset="jetson_uploads",
            folder="jetson",
            resource_type="image"
        )
        print(f"Gambar berhasil diunggah ke Cloudinary: {response['secure_url']}")
        return response['secure_url']
    except Exception as e:
        print(f"Error saat mengunggah ke Cloudinary: {e}")
        return None

# Fungsi untuk menyimpan data ke Firestore
def save_to_firestore(timestamp, image_url):
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        doc_ref = db.collection('sleep').document(date_str)
        doc_ref.set({
            str(int(timestamp)): {
                'unix_timestamp': int(timestamp),
                'url_image': image_url
            }
        }, merge=True)
        print(f"Data berhasil disimpan ke Firestore: {date_str}/{int(timestamp)}")
    except Exception as e:
        print(f"Error saat menyimpan ke Firestore: {e}")

# Fungsi untuk mengirim notifikasi ke Telegram
def send_to_telegram(image_url, caption):
    print(f"Mencoba mengirim notifikasi ke Telegram dengan URL: {image_url}")
    try:
        data = {
            'chat_id': CHANNEL_ID,
            'photo': image_url,
            'caption': caption
        }
        response = requests.post(TELEGRAM_URL, data=data)
        if response.status_code == 200:
            print("Notifikasi berhasil dikirim ke Telegram")
        else:
            print(f"Gagal mengirim notifikasi ke Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error saat mengirim ke Telegram: {e}")

# Inisialisasi model YOLO
model = YoloTRT(
    library="yolov5/build/libmyplugins.so",
    engine="yolov5/build/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

# Inisialisasi video capture
# cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap = cv2.VideoCapture('tes-vid2.mp4')
if not cap.isOpened():
    print("Error: Tidak dapat membuka video tes-vid.mp4")
    sys.exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

DETECTION_DURATION = 10
frame_count = 0
tracked_objects = {}  # {id: {'start_time': float, 'message_sent': bool}}
tracked_boxes = {}    # {id: {'centroid': tuple, 'box': list, 'class': str, 'conf': float}}
next_id = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Gagal mengambil frame dari video")
        break

    frame_count += 1
    frame_resized = cv2.resize(frame, (640, 360))

    # Buat salinan gambar untuk inferensi
    frame_for_inference = frame_resized.copy()
    detections, t = model.Inference(frame_for_inference)
    print(f"Frame {frame_count}: {len(detections)} objek terdeteksi")
    for idx, obj in enumerate(detections):
        print(f"  Deteksi {idx}: Kelas={obj['class']}, Conf={obj['conf']}, Box={obj['box']}")

    # Filter deteksi hanya untuk kelas "sleep"
    detections = [obj for obj in detections if obj['class'] == "sleep"]
    print(f"Deteksi 'sleep': {len(detections)} objek")

    # Perbarui pelacakan
    tracked_boxes, next_id = update_tracks(tracked_boxes, detections)
    current_time = time.time()

    # Perbarui tracked_objects berdasarkan tracked_boxes
    for obj_id, obj_data in tracked_boxes.items():
        if obj_id not in tracked_objects:
            tracked_objects[obj_id] = {'start_time': current_time, 'message_sent': False}
            print(f"Deteksi baru untuk ID {obj_id}")

    # Periksa setiap objek yang dilacak
    for obj_id in list(tracked_objects.keys()):
        if obj_id in tracked_boxes:
            duration = current_time - tracked_objects[obj_id]['start_time']
            print(f"ID {obj_id}: Durasi deteksi = {duration:.2f} detik, Message Sent = {tracked_objects[obj_id]['message_sent']}")
            if not tracked_objects[obj_id]['message_sent'] and duration >= DETECTION_DURATION:
                # Unggah gambar dengan bounding box
                image_url = upload_to_cloudinary(frame_for_inference)
                if image_url:
                    # Simpan data ke Firestore
                    timestamp = time.time()
                    save_to_firestore(timestamp, image_url)
                    # Kirim notifikasi ke Telegram
                    caption = f"Sleeping student detected (ID: {obj_id})"
                    send_to_telegram(image_url, caption)
                    tracked_objects[obj_id]['message_sent'] = True
        else:
            print(f"Deteksi terhenti untuk ID {obj_id}")
            del tracked_objects[obj_id]

    fps_text = "FPS: {:.2f}".format(1 / t)
    cv2.putText(frame_for_inference, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Output", frame_for_inference)  # Tampilkan gambar dengan bounding box

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
