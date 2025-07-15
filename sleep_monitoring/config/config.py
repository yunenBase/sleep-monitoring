import cloudinary
from firebase_admin import credentials, initialize_app, firestore

# Konfigurasi Cloudinary
cloudinary.config(
    cloud_name="doqvbpnf8",
    api_key="541582174476865",
    api_secret="Z4puy0FmcUZR8lXdtJ-vfKB6NMY"
)

# Konfigurasi Firebase
cred = credentials.Certificate("sleepmonitoring-ed560-firebase-adminsdk-fbsvc-6a7f045e37.json")
initialize_app(cred)
db = firestore.client()

# Konfigurasi Telegram
TOKEN = "8079449917:AAHoAEvGAJYFaqBpQBKn1xQTmFBQdQcEm1Q"
CHANNEL_ID = "-1002808476646"
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

# Konfigurasi deteksi
DETECTION_DURATION = 10
DETECTION_DURATION_CONTINUE = 20
