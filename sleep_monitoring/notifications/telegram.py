import requests
from config.config import TELEGRAM_URL, CHANNEL_ID

def send_to_telegram(image_url, caption, total_duration):
    print(f"Mencoba mengirim notifikasi ke Telegram dengan URL: {image_url}")
    try:
        data = {
            'chat_id': CHANNEL_ID,
            'photo': image_url,
            'caption': f"{caption}, Duration: {total_duration:.2f} seconds"
        }
        response = requests.post(TELEGRAM_URL, data=data)
        if response.status_code == 200:
            print("Notifikasi berhasil dikirim ke Telegram")
        else:
            print(f"Gagal mengirim notifikasi ke Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error saat mengirim ke Telegram: {e}")