import cv2
import time
import json
import numpy as np
import threading 
from flask import Flask, Response, redirect, url_for, make_response

# --- CONFIGURATION ---
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
FEEDS_FILE = "feeds.json"
WAIT_TIME_ON_CYCLE = 1  # CRITICAL: Pause in seconds after feed switch

# Arrow Button Configuration
BUTTON_COLOR = (255, 255, 255)
BUTTON_SIZE = 30
BUTTON_MARGIN = 5

app = Flask(__name__)

# --- GLOBAL STATE MANAGEMENT ---
CURRENT_FEED_INDEX = 0 
STREAM_VERSION = 0 
FEED_LOCK = threading.Lock() 

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

NUM_FEEDS = len(STREAM_FEEDS)
if NUM_FEEDS == 0:
    print("FATAL: No valid feeds loaded. Exiting.")
    exit(1)

# --- Helper Functions (Letterbox and Draw Arrow - Same as before) ---

def letterbox_frame(frame, target_width, target_height):
    source_h, source_w = frame.shape[:2]
    target_aspect = target_width / target_height
    source_aspect = source_w / source_h
    
    if source_aspect > target_aspect:
        scale_factor = target_width / source_w
        new_w = target_width
        new_h = int(source_h * scale_factor)
        padding_v = (target_height - new_h) // 2
        padding_h = 0
    else:
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
    pts = []
    if direction == "left":
        pts = np.array([
            (center_x - size//2, center_y),
            (center_x + size//2, center_y - size//2),
            (center_x + size//2, center_y + size//2)
        ], np.int32)
    elif direction == "right":
        pts = np.array([
            (center_x + size//2, center_y),
            (center_x - size//2, center_y - size//2),
            (center_x - size//2, center_y + size//2)
        ], np.int32)

    cv2.fillPoly(img, [pts], color)

# --- Video Stream Generation ---

def get_current_feed_info():
    with FEED_LOCK:
        feed = STREAM_FEEDS[CURRENT_FEED_INDEX]
        return feed['url'], feed['name'], STREAM_VERSION

def generate_frames():
    
    rtsp_url, feed_name, expected_version = get_current_feed_info()
    
    cap = cv2.VideoCapture(rtsp_url)
    
    # NEW: Try to connect up to 3 times before giving up
    for attempt in range(3):
        print(f"Attempt {attempt+1}: Opening stream {feed_name} (Version: {expected_version})")
        
        # Give a moment for connection initialization
        time.sleep(1) 
        
        if cap.isOpened():
            break
        
        # If not opened, try releasing and reconnecting (crucial for resource-constrained systems)
        if attempt < 2:
            cap.release()
            cap = cv2.VideoCapture(rtsp_url)
        
    if not cap.isOpened():
        print(f"FATAL: Could not open video source after 3 attempts: {rtsp_url}")
        return

    while True:
        
        # Check if the global state has been updated
        with FEED_LOCK:
            if expected_version != STREAM_VERSION:
                print(f"Version mismatch detected for {feed_name}. Terminating thread.")
                break
        
        success, frame = cap.read()

        if not success:
            print(f"Failed to read frame from {feed_name}. Attempting to reconnect...")
            cap.release()
            cap = cv2.VideoCapture(rtsp_url)
            time.sleep(1) 
            continue 

        # ... (Frame processing and overlay logic remains the same) ...
        display_frame, _, _ = letterbox_frame(frame, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        
        # Overlay Visual Buttons
        center_y = DISPLAY_HEIGHT // 2
        left_center_x = BUTTON_MARGIN + BUTTON_SIZE // 2
        draw_arrow(display_frame, left_center_x, center_y, BUTTON_SIZE, "left", BUTTON_COLOR)
        right_center_x = DISPLAY_WIDTH - BUTTON_MARGIN - BUTTON_SIZE // 2
        draw_arrow(display_frame, right_center_x, center_y, BUTTON_SIZE, "right", BUTTON_COLOR)
        
        # Add Status Text
        current_time = time.strftime("%H:%M:%S")
        cv2.putText(
            img=display_frame,
            text=f"{feed_name} | {current_time}",
            org=(5, DISPLAY_HEIGHT - 10),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.5,
            color=(0, 255, 0),
            thickness=1
        )

        # Encode and Yield
        (flag, encodedImage) = cv2.imencode(".jpg", display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        
        if not flag:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

    # CRITICAL: Release the capture object when the loop is broken
    cap.release()
    print(f"Stream resources released for: {feed_name}")

# --- Flask Navigation Routes (Modified) ---

def cycle_feed(direction):
    """
    Handles the cycling logic: updates index, increments version, and WAITS.
    """
    global CURRENT_FEED_INDEX, STREAM_VERSION
    
    # 1. Update state and signal termination
    with FEED_LOCK:
        if direction == 'next':
            CURRENT_FEED_INDEX = (CURRENT_FEED_INDEX + 1) % NUM_FEEDS
        elif direction == 'prev':
            CURRENT_FEED_INDEX = (CURRENT_FEED_INDEX - 1) % NUM_FEEDS
        
        STREAM_VERSION += 1
    
    print(f"Switched to {direction.upper()} feed. New index: {CURRENT_FEED_INDEX}")

    # 2. CRITICAL FIX: Pause the current thread to give the old streaming thread 
    # time to see the version change, break its loop, and call cap.release().
    print(f"Pausing for {WAIT_TIME_ON_CYCLE}s for graceful cleanup...")
    time.sleep(WAIT_TIME_ON_CYCLE) 
    
    # 3. Redirect to force the browser to establish a new connection
    return redirect(url_for('index'))

@app.route("/prev")
def prev_feed():
    return cycle_feed('prev')

@app.route("/next")
def next_feed():
    return cycle_feed('next')

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype = "multipart/x-mixed-replace; boundary=frame")
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

@app.route("/")
def index():
    """
    A simple HTML page to embed the video feed and the navigation links.
    Now includes anti-caching headers.
    """
    _, feed_name, current_version = get_current_feed_info()
    
    navigation_links = """
        <div style="margin-top: 15px;">
            <a href="/prev" style="margin-right: 50px; font-size: 1.2em;">&lt;&lt; PREV</a>
            <a href="/next" style="font-size: 1.2em;">NEXT &gt;&gt;</a>
        </div>
    """
    
    html_content = f"""
    <html>
      <head>
        <title>RPI Doorbell - Stream Navigation PoC</title>
        <style>body {{ background-color: #333; color: white; text-align: center; }}</style>
      </head>
      <body>
        <h1>Live Feed: {feed_name} (Index: {CURRENT_FEED_INDEX}/{NUM_FEEDS - 1})</h1>
        <div style="border: 2px solid red; display: inline-block;">
            <img src="/video_feed" width="{DISPLAY_WIDTH}" height="{DISPLAY_HEIGHT}">
        </div>
        {navigation_links}
        <p style="margin-top: 20px;">Stream Version: {current_version}</p>
      </body>
    </html>
    """
    
    # CRITICAL FIX: Create a response object for the main route and add anti-caching headers
    response = make_response(html_content)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

if __name__ == '__main__':
    print(f"--- Loaded {NUM_FEEDS} streams from {FEEDS_FILE} ---")
    print(f"Starting at Stream: {STREAM_FEEDS[CURRENT_FEED_INDEX]['name']}")
    print("Access the video stream at: http://<your-pi-ip>:8080/")
    
    app.run(host='0.0.0.0', port='8080', debug=False, threaded=True)