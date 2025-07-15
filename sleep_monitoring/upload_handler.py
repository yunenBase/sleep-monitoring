import time
from utils.cloud_storage import upload_to_cloudinary
from database.firestore_db import save_to_firestore_detection
from notifications.telegram import send_to_telegram

def upload_and_notify(image, obj_id, sleep_count, duration, camera_id):
    image_url = upload_to_cloudinary(image)
    if image_url:
        save_to_firestore_detection(time.time(), image_url, sleep_count, obj_id, duration, camera_id=camera_id)
        caption = f"Sleeping student detected (ID: {obj_id}, Count: {sleep_count}, Camera: {camera_id})"
        send_to_telegram(image_url, caption, duration)
        return image_url
    return None