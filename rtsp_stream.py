import cv2
import time
import json
import numpy as np # Needed for creating the black frame
from flask import Flask, Response

# --- CONFIGURATION ---
# Target dimensions for your future SPI display (Fixed)
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
FEEDS_FILE = "feeds.json"

app = Flask(__name__)

# --- NEW: Load Feeds from JSON ---
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
    # 1. Calculate ratios
    source_h, source_w = frame.shape[:2]
    target_aspect = target_width / target_height
    source_aspect = source_w / source_h

    # 2. Determine scaling and padding
    if source_aspect > target_aspect:
        # Source is wider than target (16:9 on 4:3 display). Letterbox (top/bottom padding).
        scale_factor = target_width / source_w
        new_w = target_width
        new_h = int(source_h * scale_factor)
        padding_v = (target_height - new_h) // 2
        padding_h = 0
    else:
        # Source is taller than target (4:3 on 16:9 display). Pillarbox (side padding).
        scale_factor = target_height / source_h
        new_h = target_height
        new_w = int(source_w * scale_factor)
        padding_h = (target_width - new_w) // 2
        padding_v = 0
        
    # 3. Resize and place on the black canvas
    resized_image = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Create the black canvas (B, G, R channels)
    canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
    
    # Paste the resized image onto the canvas
    canvas[padding_v:padding_v + new_h, padding_h:padding_h + new_w] = resized_image
    
    return canvas, padding_v, padding_h


def generate_frames(rtsp_url):
    """
    Connects to the specified RTSP stream URL, decodes frames, 
    applies letterboxing, and streams them as MJPEG.
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

        # 1. Apply Letterboxing
        # The output frame is guaranteed to be DISPLAY_WIDTH x DISPLAY_HEIGHT
        display_frame, v_pad, h_pad = letterbox_frame(frame, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        
        # 2. Add Status Text (adjusted for padding if needed)
        current_time = time.strftime("%H:%M:%S")
        
        # Place text at the bottom left of the actual video area (below the black bar if letterboxed)
        text_y_pos = DISPLAY_HEIGHT - 10 if v_pad == 0 else v_pad + display_frame.shape[0] - v_pad - 10
        text_x_pos = 5 if h_pad == 0 else h_pad + 5
        
        cv2.putText(
            img=display_frame,
            text=f"{DEFAULT_FEED_NAME} | {current_time}",
            org=(text_x_pos, DISPLAY_HEIGHT - 10),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.5,
            color=(0, 255, 0),
            thickness=1
        )

        # 3. Encode to JPEG
        (flag, encodedImage) = cv2.imencode(".jpg", display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        
        if not flag:
            continue

        # 4. Yield the frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

    cap.release()

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(DEFAULT_RTSP_URL),
                    mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/")
def index():
    # Note that the <img> tag keeps the output size fixed at 320x240
    return f"""
    <html>
      <head>
        <title>RPI Doorbell - Aspect Ratio Corrected</title>
        <style>body {{ background-color: #333; color: white; text-align: center; }}</style>
      </head>
      <body>
        <h1>Live Feed (Aspect Ratio Corrected): {DEFAULT_FEED_NAME}</h1>
        <div style="border: 2px solid red; display: inline-block;">
            <img src="/video_feed" width="320" height="240">
        </div>
        <p>Using Letterboxing to fit the 16:9 feed into a 4:3 frame.</p>
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