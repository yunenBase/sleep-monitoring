from flask import Flask, Response
import cv2
import time

app = Flask(__name__)

# Initialize the camera (use 0 for USB webcam, or GStreamer pipeline for CSI camera)
# For USB webcam
camera = cv2.VideoCapture(0)

# For CSI camera, uncomment the following line and comment the above line
# camera = cv2.VideoCapture('nvarguscamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! nvvidconv ! video/x-raw, format=BGR ! appsink', cv2.CAP_GSTREAMER)

def generate_frames():
    while True:
        # Read frame from the camera
        success, frame = camera.read()
        if not success:
            break
        
        # Encode the frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Yield the frame in the MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        # Add a small delay to control frame rate
        time.sleep(0.033)  # Approximately 30 fps

@app.route('/')
def index():
    # Simple HTML page to display the video stream
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jetson Nano Video Stream</title>
    </head>
    <body>
        <h1>Live Video Stream from Jetson Nano</h1>
        <img src="/video_feed" style="width:640px; height:480px;">
    </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    # Stream the video feed
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Replace '0.0.0.0' with your Jetson Nano's IP address if needed
    app.run(host='0.0.0.0', port=5000, threaded=True)