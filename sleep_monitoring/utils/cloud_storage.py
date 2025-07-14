import cloudinary.uploader
from PIL import Image
import io
import cv2

def upload_to_cloudinary(image):
    try:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)
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