import cv2
import sys
from yoloDet import YoloTRT

# Inisialisasi model YOLO
model = YoloTRT(
    library="yolov5/build/libmyplugins.so",
    engine="models/newhyp.engine",
    conf=0.5,
    yolo_ver="v5"
)

# Inisialisasi video capture (ganti 0 dengan path video lokal jika menggunakan video)
# cap = cv2.VideoCapture(0, cv2.CAP_V4L2)  
cap = cv2.VideoCapture("videos/camkanan.mp4")
if not cap.isOpened():
    print("Error: Tidak dapat membuka webcam/video")
    sys.exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

capture_count = 0  # Variabel untuk penamaan file capture

# Main loop
while True:
    ret, frame = cap.read()
    if not ret:
        print("Gagal mengambil frame dari webcam/video")
        break

    # Resize frame untuk inferensi (sesuaikan dengan kebutuhan model)
    frame_resized = cv2.resize(frame, (640, 360))
    detections, inference_time = model.Inference(frame_resized)

    # Gambar frame untuk ditampilkan
    frame_display = frame_resized.copy()

    # Gambar bounding box default YOLO dengan confidence score
    for obj in detections:
        x1, y1, x2, y2 = [int(coord) for coord in obj['box']]
        conf = obj['conf']
        class_name = obj['class']
       
    # Tampilkan frame dengan bounding box default
    cv2.imshow("YOLO Detection", frame_display)

    # Fungsi capture dengan tombol 'c'
    key = cv2.waitKey(1) & 0xFF
    if key == ord('c'):
        capture_count += 1
        image_name = f'capture_{capture_count}.png'
        cv2.imwrite(image_name, frame)
        print(f"Gambar berhasil disimpan sebagai {image_name}")

    # Keluar dengan tombol 'q'
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()