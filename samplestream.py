import numpy as np
import cv2
import time
from flask import Flask, Response

# --- SIMULATION AND STREAMING SETUP ---

# 1. Define simulated display properties
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
COLOR_CHANNELS = 3  # For BGR (OpenCV default)

app = Flask(__name__)

def generate_frames():
    """
    Simulates getting a frame from the PyAV decoder (later) and streaming it.
    """
    while True:
        # 1. Initialize the simulated framebuffer (NumPy array)
        # This is where your decoded H.264/H.265 frame would go
        frame = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, COLOR_CHANNELS), dtype=np.uint8)

        # 2. Simulate Drawing: Draw a dynamic green rectangle and timestamp
        
        # Draw a bright green rectangle
        frame[50:150, 50:250] = [0, 255, 0]  # BGR format: Green

        # Add a dynamic timestamp
        current_time = time.strftime("%H:%M:%S")
        cv2.putText(
            img=frame,
            text=current_time,
            org=(10, 30),  # Position
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.7,
            color=(255, 255, 255),  # White text
            thickness=2
        )
        
        # 3. Encode the NumPy array into JPEG format
        # This is crucial for transmitting the image data efficiently
        (flag, encodedImage) = cv2.imencode(".jpg", frame)
        
        # If encoding fails, skip this frame
        if not flag:
            continue

        # 4. Yield the frame data for the HTTP response
        # This uses the multipart/x-mixed-replace format for continuous streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    """
    The main route for the browser to fetch the streaming video feed.
    """
    return Response(generate_frames(),
                    mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/")
def index():
    """
    A simple HTML page to embed the video feed.
    """
    return """
    <html>
      <head>
        <title>RPI Zero 2W Doorbell Simulator</title>
      </head>
      <body>
        <h1>Simulated Framebuffer Stream</h1>
        <img src="/video_feed" width="320" height="240">
        <p>This stream simulates the output intended for your SPI display.</p>
      </body>
    </html>
    """

if __name__ == '__main__':
    # Running on 0.0.0.0 makes it accessible from other devices on the network
    # Use port 8080 or any other free port
    print("--- Starting Flask Streamer ---")
    print("Access the video stream at: http://127.0.0.1:8080/")
    
    # Set threaded=True for better handling of multiple requests
    app.run(host='0.0.0.0', port='8080', debug=False, threaded=True)
