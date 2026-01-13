import time
import json
import cv2
from PIL import Image
import RPi.GPIO as GPIO 
import signal
import requests
import os
import datetime
import threading
from dotenv import load_dotenv

# Luma Libraries
from luma.core.render import canvas
from luma.core.interface.serial import spi
from luma.lcd.device import st7735

# --- CONFIGURATION ---
FEEDS_FILE = "feeds.json"
LCD_WIDTH = 128
LCD_HEIGHT = 128
device = None

# Load Environment Variables
if os.path.exists(',env'):
    load_dotenv(',env')
else:
    load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHATID = os.getenv("TELEGRAM_CHATID")

# Waveshare 1.44" HAT Pin Defs (BCM)
SPI_DC_PIN = 25
SPI_RST_PIN = 27
SPI_BL_PIN = 24

# Button Pins
KEY_NEXT_PIN = 21  # Key 1
KEY_PREV_PIN = 20  # Key 2
KEY_RELOAD_PIN = 16 # Key 3 (Now Snapshot)

# --- GLOBAL STATE ---
feeds = []
current_feed_index = 0
last_button_press_time = 0
BUTTON_DEBOUNCE_TIME = 0.3 # Seconds

# --- 1. GPIO SETUP (Manual & Clean) ---
# We do this FIRST to clear any previous errors
try:
    GPIO.setmode(GPIO.BCM)
    # Clean specific pins if they were left open, or just proceed
except Exception:
    pass

# Setup Button Inputs
GPIO.setup(KEY_NEXT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY_PREV_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY_RELOAD_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- 2. SETUP DISPLAY (Luma) ---
# Luma will detect BCM is already set and use it
serial_interface = spi(
    port=0,          
    device=0,        
    gpio_DC=SPI_DC_PIN,
    gpio_RST=SPI_RST_PIN,
    gpio_backlight=SPI_BL_PIN 
)

device = st7735(
    serial_interface,
    rotate=0,
    width=LCD_WIDTH,
    height=LCD_HEIGHT,
    h_offset=1,   
    v_offset=2,   
    bgr=True
)

# --- 3. HELPER FUNCTIONS ---
def load_feeds():
    global feeds, current_feed_index
    try:
        with open(FEEDS_FILE, 'r') as f:
            feeds = json.load(f)
    except Exception as e:
        print(f"Error loading feeds: {e}")
        feeds = []

    if not feeds:
        feeds = [{"name": "No Config", "url": ""}]
    
    # Correction if index is out of bounds after reload
    if current_feed_index >= len(feeds):
        current_feed_index = 0
    
    print(f"Loaded {len(feeds)} feeds.")

def check_buttons():
    """
    Checks if buttons are pressed. Returns 'next', 'prev', 'snapshot', or None.
    Includes software debouncing.
    """
    global last_button_press_time, current_feed_index
    
    now = time.time()
    if (now - last_button_press_time) < BUTTON_DEBOUNCE_TIME:
        return None

    action = None
    
    # Logic: GPIO.LOW means pressed (because of PUD_UP)
    if GPIO.input(KEY_NEXT_PIN) == 0:
        print(">>> Button: NEXT")
        current_feed_index = (current_feed_index + 1) % len(feeds)
        action = 'switch'
        last_button_press_time = now
        
    elif GPIO.input(KEY_PREV_PIN) == 0:
        print(">>> Button: PREV")
        current_feed_index = (current_feed_index - 1) % len(feeds)
        action = 'switch'
        last_button_press_time = now
        
    elif GPIO.input(KEY_RELOAD_PIN) == 0:
        print(">>> Button: SNAPSHOT")
        action = 'snapshot'
        last_button_press_time = now
        
    return action

def send_snapshot_thread(frame_bgr, feed_name):
    """
    Background worker to save and send the snapshot.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHATID:
        print("Telegram Warning: Missing credentials, cannot send snapshot.")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    caption = f"Snapshot: {feed_name}\nTime: {timestamp}"
    
    filename = "/tmp/videopi_snapshot.jpg"
    
    try:
        # Save full resolution frame
        cv2.imwrite(filename, frame_bgr)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(filename, 'rb') as f:
            files = {'photo': f}
            data = {
                "chat_id": TELEGRAM_CHATID,
                "caption": caption
            }
            print(f"Sending snapshot to Telegram ({feed_name})...")
            response = requests.post(url, data=data, files=files)
            if response.status_code == 200:
                print("Snapshot sent successfully.")
            else:
                print(f"Failed to send snapshot: {response.text}")
                
    except Exception as e:
        print(f"Error sending snapshot: {e}")

def draw_ui(cv_frame, feed_name, status_text=None):
    # Black Bottom Bar
    cv2.rectangle(cv_frame, (0, 115), (128, 128), (0, 0, 0), -1)
    
    # Feed Name
    disp_name = (feed_name[:12] + '..') if len(feed_name) > 12 else feed_name
    cv2.putText(cv_frame, disp_name, (2, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
    
    # Optional Status Text (e.g. "SNAP!")
    if status_text:
         cv2.putText(cv_frame, status_text, (80, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)

    return cv_frame

# --- 4. MAIN LOOP ---
def run_doorbell():
    load_feeds()
    device.backlight(True)
    
    while True:
        # --- CONNECT PHASE ---
        current_feed = feeds[current_feed_index]
        url = current_feed['url']
        name = current_feed['name']
        
        print(f"Connecting to: {name}")
        
        # UI: Connecting...
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            draw.text((10, 50), f"Loading...", fill="white")
            draw.text((10, 65), f"{name}", fill="green")

        cap = cv2.VideoCapture(url)
        
        if not cap.isOpened():
             print("Connection failed. Waiting 2s before retry or button press...")
             start_fail = time.time()
             # While waiting, we must still poll buttons so user isn't stuck!
             while (time.time() - start_fail) < 2.0:
                 if check_buttons() == 'switch':
                     break
                 time.sleep(0.1)
             if cap.isOpened(): cap.release()
             continue # Loop back to start (picks up new index if button pressed)

        # --- STREAM PHASE ---
        snapshot_feedback_timer = 0
        
        while True:
            # 1. Check Buttons
            btn_action = check_buttons()
            if btn_action == 'switch':
                break # Break inner loop -> Re-connect to new feed
            
            # 2. Read Frame
            ret, frame = cap.read()
            
            if not ret:
                print("Stream ended or dropped.")
                break 
            
            # Handle Snapshot
            if btn_action == 'snapshot':
                # Launch thread to avoid freezing the stream
                t = threading.Thread(target=send_snapshot_thread, args=(frame.copy(), name))
                t.start()
                snapshot_feedback_timer = time.time() # Start showing feedback

            # 3. Process & Display
            frame_resized = cv2.resize(frame, (LCD_WIDTH, LCD_HEIGHT), interpolation=cv2.INTER_LINEAR)
            
            # Determine feedback text
            status = None
            if time.time() - snapshot_feedback_timer < 1.0: # Show for 1 second
                status = "SNAP!"
                
            frame_resized = draw_ui(frame_resized, name, status)
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            device.display(Image.fromarray(frame_rgb))
            
        cap.release()
        print(f"Released: {name}")

        # Show feedback while switching
        with canvas(device) as draw:
             draw.rectangle(device.bounding_box, outline="black", fill="black")
             draw.text((30, 60), "Switching...", fill="yellow")

def cleanup_and_exit(signum, frame):
    """Signal handler function to gracefully shut down the display."""
    global device
    print(f"\n--- SIGTERM/Interrupt detected. Shutting down gracefully... ---")

    if device:
        # 1. Blank the display immediately
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
            draw.text((10, 60), "Display OFF", fill="red")

        # 2. Turn off backlight
        device.backlight(False)

    # 3. Clean up GPIO for safety (optional, but good practice)
    try:
        GPIO.cleanup()
    except:
        pass

    print("Cleanup complete. Exiting.")
    # Exit the application cleanly
    exit(0)

if __name__ == "__main__":
    print("--- Doorbell Started (Polling Mode) ---")
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)

    try:
        run_doorbell()
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
        print("GPIO Cleaned.")
