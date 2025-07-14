# server.py
import cv2
import socket
import pickle
import struct
import time

# Inisialisasi soket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0', 5000))
server_socket.listen(5)
print("Menunggu koneksi...")

# Gunakan backend V4L2 untuk menghindari GStreamer
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
if not cap.isOpened():
    print("Error: Tidak dapat membuka webcam")
    exit()

# Atur resolusi (opsional, sesuaikan jika perlu)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

client_socket, addr = server_socket.accept()
print(f"Terhubung ke {addr}")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal mengambil frame dari webcam")
            break

        # Kompres frame untuk mengurangi ukuran data
        frame = cv2.resize(frame, (320, 240))  # Resize untuk efisiensi
        data = pickle.dumps(frame)
        message_size = struct.pack("L", len(data))

        try:
            # Kirim ukuran data dan frame
            client_socket.sendall(message_size + data)
        except Exception as e:
            print(f"Error mengirim data: {e}")
            break

        # Tambahkan jeda kecil untuk mencegah overload
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Streaming dihentikan oleh pengguna")

finally:
    cap.release()
    client_socket.close()
    server_socket.close()