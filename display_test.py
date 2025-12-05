import time
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont, Image

# --- 1. CONFIGURATION BASED ON WAVESHARE HAT ---

# SPI Interface setup (using BCM GPIO numbering)
# SCLK: 11, MOSI: 10, CS: 8 (Standard SPI pins on bus 0, device 0)
# DC (Data/Command): 25, RST (Reset): 27 
serial = spi(
    port=0,          # SPI Bus 0
    device=0,        # SPI Device 0 (CS 8)
    gpio_DC=25,      # DC pin (BCM 25)
    gpio_RST=27,     # RST pin (BCM 27)
)

# Initialize the ST7735S display device
# The Waveshare 1.44" uses the ST7735S driver (often called 'green tab' variant).
# The key is setting the correct offsets for the 128x128 window.
device = st7735(
    serial, 
    rotate=0,
    width=128, 
    height=128, 
    # Recommended offsets for the Waveshare 1.44" (128x128 ST7735S panel)
    h_offset=2, 
    v_offset=3,
    bgr=True, # The Waveshare uses BGR format internally, which needs to be specified
    active_low=True # Backlight pin 24 is often active-low, but we won't directly control it here.
                    # This parameter mainly affects a dedicated backlight GPIO if used.
)

# --- 2. DRAWING LOGIC ---

def draw_hello_world():
    """Draws 'Hello World' on the display and then clears it."""
    
    print("Drawing 'Hello World' with ST7735S configuration...")
    
    # Try to load a simple font. Fallback to default if needed.
    try:
        # Load a standard system font for better clarity
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except IOError:
        # If system font not found, use default PIL font
        font = ImageFont.load_default()
            
    # Create an image canvas tied to the display device
    with canvas(device) as draw:
        # Draw a black background
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        
        # Draw the text
        draw.text((5, 45), "Hello World", fill="white", font=font)
        draw.text((5, 65), "ST7735S Test", fill="yellow", font=font)
        
        # Draw a bounding box for debugging alignment
        draw.rectangle(device.bounding_box, outline="red")
        
    print("Displaying for 5 seconds...")
    time.sleep(5)

    # Clear the screen after 5 seconds
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
    
    print("Test complete.")

# --- 3. MAIN EXECUTION ---
if __name__ == '__main__':
    # Ensure RPi.GPIO is installed if we later use the buttons or backlight control
    # pip3 install RPi.GPIO

    try:
        draw_hello_world()
        
    except KeyboardInterrupt:
        print("\nExiting program.")
        
    except Exception as e:
        print(f"An error occurred. Check your wiring and SPI/GPIO settings. Error: {e}")
        # Attempt to clear the display on error
        try:
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="black", fill="black")
        except:
            pass