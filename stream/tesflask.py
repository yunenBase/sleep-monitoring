from flask import Flask, Response
import cv2
import time

app = Flask(__name__)

# Inisialisasi webcam
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
if not cap.isOpened():
    print("Error: Tidak dapat membuka webcam")
    exit()

# Atur resolusi rendah untuk efisiensi
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

def generate_frames():
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal mengambil frame")
            break
        
        # Encode frame ke JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Kirim frame sebagai MJPEG stream
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        # Jeda kecil untuk mengurangi beban
        time.sleep(0.03)

@app.route('/')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Ganti '0.0.0.0' agar dapat diakses dari jaringan
    print("Server berjalan. Akses di http://<JETSON_IP>:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True)