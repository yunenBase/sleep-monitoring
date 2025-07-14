from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Token dari BotFather
TOKEN = "7744704117:AAFiwWyI7jpw3VcF013ae_T4CPUHLp1eDT4"

# Fungsi untuk memulai bot
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Halo! Saya adalah Sleep Detector Bot. Kirimkan gambar mahasiswa yang tertidur!")

# Fungsi untuk menerima gambar dari laptop
async def receive_photo(update: Update, context: CallbackContext) -> None:
    file = await update.message.photo[-1].get_file()
    await file.download_to_drive("received_image.jpg")
    await update.message.reply_text("Gambar diterima!")

# Setup bot
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))

    app.run_polling()

if __name__ == '__main__':
    main()
