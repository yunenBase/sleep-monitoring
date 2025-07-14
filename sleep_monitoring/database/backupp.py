from config.config import db
from datetime import datetime

def save_to_firestore_detection(date_str, timestamp, image_url, sleep_count, obj_id, total_duration, coords_rel=None, camera_id=None):
    try:
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