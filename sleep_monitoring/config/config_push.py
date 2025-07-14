import cloudinary
from firebase_admin import credentials, initialize_app, firestore

# Konfigurasi Cloudinary
cloudinary.config(
    cloud_name="",
    api_key="",
    api_secret=""
)

# Konfigurasi Firebase
cred = credentials.Certificate("")
initialize_app(cred)
db = firestore.client()

# Konfigurasi Telegram
TOKEN = ""
CHANNEL_ID = ""
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

# Konfigurasi deteksi
DETECTION_DURATION = 3
