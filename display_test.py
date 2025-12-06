import time
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont

# --- 1. CONFIGURATION BASED ON WAVESHARE HAT ---
serial = spi(
    port=0,          
    device=0,        # CS 8
    gpio_DC=25,      # DC pin (BCM 25)
    gpio_RST=27,     # RST pin (BCM 27)
)

# Initialize the ST7735S display device
device = st7735(
    serial, 
    rotate=0,
    width=128, 
    height=128, 
    # *** ADJUSTED OFFSETS FOR 128x128 ST7735S (The fix) ***
    h_offset=1,   # Reduced from 2
    v_offset=2,   # Reduced from 3
    bgr=True,     # Keep BGR format
)

# --- 2. DRAWING LOGIC (Same as before) ---
def draw_hello_world():
    print("Drawing 'Hello World' with ADJUSTED offsets (1, 2)...")
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except IOError:
        font = ImageFont.load_default()
            
    with canvas(device) as draw:
        # Draw a black background
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        
        # Draw the text
        draw.text((5, 45), "Hello World", fill="white", font=font)
        draw.text((5, 65), "Offsets (1, 2) Test", fill="yellow", font=font)
        
        # Draw a bounding box around the 128x128 area (should align perfectly now)
        draw.rectangle(device.bounding_box, outline="red")
        
    print("Displaying for 5 seconds...")
    time.sleep(5)

    # Clear the screen after 5 seconds
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
    
    print("Test complete.")

# --- 3. MAIN EXECUTION ---
if __name__ == '__main__':
    try:
        draw_hello_world()
        
    except Exception as e:
        print(f"An error occurred: {e}")
        try:
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="black", fill="black")
        except:
            pass