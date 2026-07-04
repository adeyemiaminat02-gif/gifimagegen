import os
import logging
from io import BytesIO
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary storage for users' images: {user_id: [BytesIO, BytesIO, ...]}
USER_IMAGES = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    USER_IMAGES[user_id] = []
    await update.message.reply_text(
        "👋 Welcome! Send me 2 or more images, one by one. "
        "When you're finished, type /makegif to compile them into an animated GIF."
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Initialize list if it doesn't exist
    if user_id not in USER_IMAGES:
        USER_IMAGES[user_id] = []
        
    # Get the highest resolution photo sent
    photo_file = await update.message.photo[-1].get_file()
    
    # Download file into memory
    image_bytes = BytesIO()
    await photo_file.download_to_memory(out=image_bytes)
    image_bytes.seek(0)
    
    USER_IMAGES[user_id].append(image_bytes)
    count = len(USER_IMAGES[user_id])
    
    await update.message.reply_text(f"📸 Image {count} received! Add more or type /makegif.")

async def make_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id not in USER_IMAGES or len(USER_IMAGES[user_id]) < 2:
        await update.message.reply_text("❌ Please send at least 2 images before using /makegif.")
        return
    
    await update.message.reply_text("⏳ Processing your GIF... please wait.")
    
    try:
        frames = []
        for img_bytes in USER_IMAGES[user_id]:
            img_bytes.seek(0)
            img = Image.open(img_bytes)
            # Convert to RGB to ensure uniform formatting
            if img.mode != 'RGB':
                img = img.convert('RGB')
            frames.append(img)
            
        # Target sizing based on the first image
        target_size = frames[0].size
        resized_frames = [f.resize(target_size, Image.Resampling.LANCZOS) for f in frames]
        
        # Save GIF into memory
        gif_io = BytesIO()
        resized_frames[0].save(
            gif_io,
            format='GIF',
            append_images=resized_frames[1:],
            save_all=True,
            duration=500,  # 500ms per frame
            loop=0         # Infinite loop
        )
        gif_io.seek(0)
        gif_io.name = "created.gif"
        
        # Send GIF back to user
        await update.message.reply_animation(animation=gif_io, caption="🎉 Here is your GIF!")
        
    except Exception as e:
        logger.error(f"Error producing GIF: {e}")
        await update.message.reply_text("⚠️ An error occurred while creating your GIF.")
        
    finally:
        # Clear memory cache for this user
        USER_IMAGES[user_id] = []

def main():
    # Retrieve token from environment variables
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("makegif", make_gif))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    logger.info("Bot starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
