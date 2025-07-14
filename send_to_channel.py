import sys
import cv2
import requests
import os
from yoloDet import YoloTRT
from datetime import datetime
import time

model = YoloTRT(
    library="yolov5/build/libmyplugins.so",
    engine="yolov5/build/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

TOKEN = "7744704117:AAFiwWyI7jpw3VcF013ae_T4CPUHLp1eDT4"
CHANNEL_ID = "-1002516589658"
url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

# Folder to save images
SAVE_FOLDER = "tertidur"
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)
    print(f"Folder {SAVE_FOLDER} created")

# Gunakan input video lokal
cap = cv2.VideoCapture('tes-vid2.mp4')  # Ganti dengan path video lokalmu
if not cap.isOpened():
    print("Error: Tidak dapat membuka video tes-vid2.mp4")
    sys.exit()

# Set resolusi video output ke 720x480
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

def send_to_telegram(image_path, caption):
    """Mengirimkan foto ke channel Telegram."""
    print(f"Mencoba mengirim foto: {image_path}")
    try:
        with open(image_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': CHANNEL_ID,
                'caption': caption
            }
            response = requests.post(url, data=data, files=files)
            if response.status_code == 200:
                print("Foto berhasil dikirim ke Telegram")
            else:
                print(f"Gagal mengirim foto: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error saat mengirim ke Telegram: {e}")

# Variabel untuk melacak deteksi
detection_start_time = None
message_sent = False
DETECTION_DURATION = 10  # Durasi deteksi dalam detik
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Gagal mengambil frame dari video")
        break

    frame_count += 1
    # Resize frame ke ukuran 720x480
    frame_resized = cv2.resize(frame, (640, 640))

    # Inference model dan ambil waktu
    detections, t = model.Inference(frame_resized)

    # Cek apakah ada deteksi
    object_detected = len(detections) > 0
    print(f"Frame {frame_count}: {len(detections)} objek terdeteksi")
    for obj in detections:
        print(f"  Kelas: {obj['class']}, Conf: {obj['conf']}, Box: {obj['box']}")

    # Logika untuk melacak durasi deteksi
    current_time = time.time()
    if object_detected:
        if detection_start_time is None:
            detection_start_time = current_time
            print("Deteksi dimulai")
        elif (current_time - detection_start_time) >= DETECTION_DURATION and not message_sent:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(SAVE_FOLDER, f"detected_{timestamp}.jpg")
            
            # Simpan frame sebagai gambar
            success = cv2.imwrite(image_path, frame_resized)
            print(f"Mencoba menyimpan {image_path} - Berhasil: {success}")
            
            if success:
                # Kirim gambar ke Telegram
                # caption = f"Objek terdeteksi selama 5 detik pada {timestamp}"
                caption = f"Sleeping student detected"
                send_to_telegram(image_path, caption)
                message_sent = True
    else:
        if detection_start_time is not None:
            print("Deteksi terhenti")
        detection_start_time = None
        message_sent = False

    # Tampilkan FPS di atas frame
    fps_text = "FPS: {:.2f}".format(1 / t)
    cv2.putText(frame_resized, fps_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Tampilkan frame dengan deteksi
    cv2.imshow("Output", frame_resized)

    # Tekan 'q' untuk keluar
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()