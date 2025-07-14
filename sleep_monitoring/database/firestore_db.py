from config.config import db
from datetime import datetime
import uuid

def save_to_firestore_detection(timestamp, image_url, sleep_count, obj_id, total_duration, coords_rel=None, camera_id=None):
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        doc_ref = db.collection('sleep').document(date_str)
        data = {
            str(int(timestamp)): {
                'unix_timestamp': int(timestamp),
                'url_image': image_url,
                'sleep_count': sleep_count,
                'object_id': obj_id,
                'total_duration': total_duration,
                'coords_rel': coords_rel or {},  # Tambahkan koordinat relatif, default kosong jika None
                'camera_id': camera_id  # Tambahkan camera_id
            }
        }
        doc_ref.set(data, merge=True)
        print(f"Data deteksi disimpan ke Firestore (sleep): {date_str}/{int(timestamp)}, ID: {obj_id}, Sleep Count: {sleep_count}, Duration: {total_duration:.2f} detik, Coords: {coords_rel}, Camera ID: {camera_id}")
    except Exception as e:
        print(f"Error saat menyimpan ke Firestore (sleep): {e}")

def save_to_firestore_duration(start_timestamp, end_timestamp, obj_id, camera_id=None):
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        # Gunakan kombinasi camera_id dan start_timestamp sebagai ID dokumen
        unique_id = f"{camera_id}_{int(start_timestamp)}"
        doc_ref = db.collection('duration').document(date_str)
        data = {
            unique_id: {
                'start_timestamp': int(start_timestamp),
                'end_timestamp': int(end_timestamp),
                'duration': end_timestamp - start_timestamp,
                'camera_id': camera_id
            }
        }
        doc_ref.set(data, merge=True)
        print(f"Data durasi disimpan ke Firestore (duration): {date_str}/{unique_id}, Start: {int(start_timestamp)}, End: {int(end_timestamp)}, Duration: {(end_timestamp - start_timestamp):.2f} detik, Camera ID: {camera_id}")
    except Exception as e:
        print(f"Error saat menyimpan ke Firestore (duration): {e}")
