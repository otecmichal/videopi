import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHATID = os.getenv("TELEGRAM_CHATID")


def send_telegram_message(message, image_path=None):
    """
    Sends a message to the configured Telegram chat. 
    If image_path is provided, sends the image with the message as a caption.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
        return
    if not TELEGRAM_CHATID:
        print("Error: TELEGRAM_CHATID not found in environment variables.")
        return

    if image_path:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        try:
            with open(image_path, 'rb') as f:
                files = {'photo': f}
                data = {
                    "chat_id": TELEGRAM_CHATID,
                    "caption": message
                }
                response = requests.post(url, data=data, files=files)
        except FileNotFoundError:
            print(f"Error: File not found at {image_path}")
            return
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHATID,
            "text": message
        }
        response = requests.post(url, json=payload)

    try:
        response.raise_for_status()
        print(f"Message{' (with image)' if image_path else ''} sent successfully to chat ID {TELEGRAM_CHATID}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message: {e}")
        try:
            print(f"Response: {response.text}")
        except:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_telegram.py \"<message>\" [optional_image_path]")
        sys.exit(1)
    
    msg = sys.argv[1]
    img_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    send_telegram_message(msg, img_path)
