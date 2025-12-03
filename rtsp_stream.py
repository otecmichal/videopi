import cv2
import time
import json
import numpy as np
from flask import Flask, Response

# --- CONFIGURATION ---
# Target dimensions for your future SPI display (Fixed 4:3)
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
FEEDS_FILE = "feeds.json"

# Arrow Button Configuration
BUTTON_COLOR = (255, 255, 255)  # White
BUTTON_ALPHA = 0.5             # Translucency (ignored by basic OpenCV drawing)
BUTTON_SIZE = 25               # Size of the arrow triangle
BUTTON_MARGIN = 10              # Distance from the edge

app = Flask(__name__)

# --- Load Feeds from JSON (Same as before) ---
try:
    with open(FEEDS_FILE, 'r') as f:
        STREAM_FEEDS = json.load(f)
except FileNotFoundError:
    print(f"FATAL: The configuration file '{FEEDS_FILE}' was not found.")
    STREAM_FEEDS = []
except json.JSONDecodeError:
    print(f"FATAL: Error decoding JSON from '{FEEDS_FILE}'. Check file format.")
    STREAM_FEEDS = []

if not STREAM_FEEDS:
    print("WARNING: No valid feeds loaded. Using a dummy URL to prevent crash.")
    DEFAULT_RTSP_URL = "rtsp://invalid"
    DEFAULT_FEED_NAME = "NO FEED"
else:
    DEFAULT_RTSP_URL = STREAM_FEEDS[0]['url']
    DEFAULT_FEED_NAME = STREAM_FEEDS[0]['name']

# ----------------------------------

def letterbox_frame(frame, target_width, target_height):
    """
    Scales the input frame to fit the target dimensions while preserving 
    its aspect ratio, adding black bars (letterboxing) if necessary.
    """
    source_h, source_w = frame.shape[:2]
    target_aspect = target_width / target_height
    source_aspect = source_w / source_h
    
    if source_aspect > target_aspect:
        # Letterbox (top/bottom padding)
        scale_factor = target_width / source_w
        new_w = target_width
        new_h = int(source_h * scale_factor)
        padding_v = (target_height - new_h) // 2
        padding_h = 0
    else:
        # Pillarbox (side padding)
        scale_factor = target_height / source_h
        new_h = target_height
        new_w = int(source_w * scale_factor)
        padding_h = (target_width - new_w) // 2
        padding_v = 0
        
    resized_image = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
    canvas[padding_v:padding_v + new_h, padding_h:padding_h + new_w] = resized_image
    
    return canvas, padding_v, padding_h

def draw_arrow(img, center_x, center_y, size, direction, color):
    """
    Draws a filled triangle arrow pointing left or right.
    """
    pts = []
    
    if direction == "left":
        # Points for a left-pointing triangle
        pts = np.array([
            (center_x - size//2, center_y),          # Tip
            (center_x + size//2, center_y - size//2), # Top corner
            (center_x + size//2, center_y + size//2)  # Bottom corner
        ], np.int32)
    elif direction == "right":
        # Points for a right-pointing triangle
        pts = np.array([
            (center_x + size//2, center_y),          # Tip
            (center_x - size//2, center_y - size//2), # Top corner
            (center_x - size//2, center_y + size//2)  # Bottom corner
        ], np.int32)

    # Reshape and draw the filled polygon
    cv2.fillPoly(img, [pts], color)


def generate_frames(rtsp_url):
    """
    Connects to the specified RTSP stream URL, decodes frames, 
    applies letterboxing, overlays controls, and streams them as MJPEG.
    """
    cap = cv2.VideoCapture(rtsp_url)
    time.sleep(2) 

    if not cap.isOpened():
        print(f"Error: Could not open video source: {rtsp_url}")
        return

    while True:
        success, frame = cap.read()

        if not success:
            print("Failed to read frame - stream might have ended or network issue.")
            break

        # 1. Apply Letterboxing (Output is 320x240)
        display_frame, v_pad, h_pad = letterbox_frame(frame, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        
        # --- 2. Overlay Visual Buttons ---
        
        # Calculate vertical center of the frame
        center_y = DISPLAY_HEIGHT // 2
        
        # LEFT ARROW Button
        left_center_x = BUTTON_MARGIN + BUTTON_SIZE // 2
        draw_arrow(
            img=display_frame, 
            center_x=left_center_x, 
            center_y=center_y, 
            size=BUTTON_SIZE, 
            direction="left", 
            color=BUTTON_COLOR
        )
        
        # RIGHT ARROW Button
        right_center_x = DISPLAY_WIDTH - BUTTON_MARGIN - BUTTON_SIZE // 2
        draw_arrow(
            img=display_frame, 
            center_x=right_center_x, 
            center_y=center_y, 
            size=BUTTON_SIZE, 
            direction="right", 
            color=BUTTON_COLOR
        )
        
        # --- 3. Add Status Text ---
        current_time = time.strftime("%H:%M:%S")
        cv2.putText(
            img=display_frame,
            text=f"{DEFAULT_FEED_NAME} | {current_time}",
            org=(5, DISPLAY_HEIGHT - 10), # Always at the bottom left
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.5,
            color=(0, 255, 0),
            thickness=1
        )

        # 4. Encode and Yield
        (flag, encodedImage) = cv2.imencode(".jpg", display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        
        if not flag:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

    cap.release()

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(DEFAULT_RTSP_URL),
                    mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/")
def index():
    return f"""
    <html>
      <head>
        <title>RPI Doorbell - Visual Controls PoC</title>
        <style>body {{ background-color: #333; color: white; text-align: center; }}</style>
      </head>
      <body>
        <h1>Live Feed with Touch Areas: {DEFAULT_FEED_NAME}</h1>
        <div style="border: 2px solid red; display: inline-block;">
            <img src="/video_feed" width="320" height="240">
        </div>
        <p>White arrows show touch zones for cycling streams.</p>
      </body>
    </html>
    """

if __name__ == '__main__':
    if DEFAULT_RTSP_URL == "rtsp://invalid":
        print("Please fix feeds.json and restart.")
    else:
        print(f"--- Defaulting to Stream: {DEFAULT_FEED_NAME} ({DEFAULT_RTSP_URL}) ---")
        print("Stream available at: http://<your-pi-ip>:8080/")
        app.run(host='0.0.0.0', port='8080', debug=False, threaded=True)