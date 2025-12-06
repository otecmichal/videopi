import RPi.GPIO as GPIO
import time
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
import signal

# --- CONFIGURATION (Must match doorbell_buttons.py) ---
SPI_DC_PIN = 25
SPI_RST_PIN = 27
SPI_BL_PIN = 24

LCD_WIDTH = 128
LCD_HEIGHT = 128

device = None

# Suppress warnings that might appear before main script runs
GPIO.setwarnings(False) 

# --- 1. SETUP DISPLAY (Minimal) ---
def setup_display():
    try:
        # Luma initializes BCM mode and GPIO setup
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
        device.backlight(True)
        return device

    except Exception as e:
        # If SPI fails (e.g., hardware not ready), just exit gracefully
        print(f"Splash screen setup failed: {e}")
        return None

# --- 2. DRAW THE SPLASH SCREEN ---
def draw_splash(device):
    if not device:
        return

    print("Displaying splash screen...")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")

        # Simple text splash:
        draw.text((10, 30), "RPI Doorbell", fill="yellow")
        draw.text((10, 50), "Loading...", fill="white")
        draw.text((10, 90), "Wait for feed...", fill="gray")

# --- SIGNAL HANDLER ---
def cleanup_and_exit(signum, frame):
    """Signal handler function to gracefully shut down the splash screen."""
    global device
    print(f"\n--- SIGTERM detected in splash.py. Stopping display... ---")
    
    if device:
        # 1. Blank the display immediately
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
        
        # 2. Turn off backlight
        device.backlight(False)
    
    # Clean up GPIO (Optional, but safe)
    try:
        GPIO.cleanup()
    except:
        pass
        
    print("Splash cleanup complete. Exiting.")
    # Exit the application cleanly
    exit(0)

# --- 3. MAIN EXECUTION ---
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    device = setup_display()
    draw_splash(device)

    # Keep the script running forever so systemd doesn't stop the screen
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
