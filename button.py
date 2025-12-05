import RPi.GPIO as GPIO
import time
import sys

# --- Pin Configuration (BCM Numbering) ---
BUTTON_PIN = 16    # Key 1: Input to test physical connection
BACKLIGHT_PIN = 24 # Backlight: Output to test physical connection
BLINK_INTERVAL = 0.5

def gpio_test():
    """Tests both input (button) and output (backlight) connections."""
    
    # Use BCM pin numbering
    GPIO.setmode(GPIO.BCM)
    
    try:
        # 1. SETUP OUTPUT (Backlight)
        GPIO.setup(BACKLIGHT_PIN, GPIO.OUT)
        
        # 2. SETUP INPUT (Button)
        # FIX: Corrected GPIO.PULL_UP to GPIO.PUD_UP
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
        
        print(f"GPIO Test Started: Button (BCM {BUTTON_PIN}) | Backlight (BCM {BACKLIGHT_PIN})")
        print("Press Key 1 (BCM 20) to see the state change.")
        print("Press Ctrl+C to stop.\n")

        last_button_state = GPIO.input(BUTTON_PIN)
        
        while True:
            # --- Backlight Blinking Logic ---
            # Active-LOW assumed: Toggle between LOW (ON) and HIGH (OFF)
            is_on = GPIO.input(BACKLIGHT_PIN) == GPIO.LOW
            
            if is_on:
                GPIO.output(BACKLIGHT_PIN, GPIO.HIGH) # Turn OFF
            else:
                GPIO.output(BACKLIGHT_PIN, GPIO.LOW)  # Turn ON
            
            # --- Button Read Logic ---
            current_button_state = GPIO.input(BUTTON_PIN)
            
            if current_button_state != last_button_state:
                # Clear line and print new state
                sys.stdout.write('\r' + ' ' * 80)
                status = "PRESSED" if current_button_state == GPIO.LOW else "RELEASED"
                state_str = 'LOW' if current_button_state == GPIO.LOW else 'HIGH'
                print(f"\r[ BUTTON {status:<8} ] State: {state_str} ({current_button_state}) | Backlight is now {'ON' if not is_on else 'OFF'}", end='')
                last_button_state = current_button_state
            else:
                # Update backlight status display without triggering a button event
                sys.stdout.write('\r' + ' ' * 80)
                print(f"\r[ BUTTON RELEASED ] State: HIGH ({last_button_state}) | Backlight is now {'ON' if not is_on else 'OFF'}", end='')
            
            time.sleep(BLINK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\nTest stopped by user.")
        
    finally:
        # CRITICAL: Clean up GPIO settings and ensure backlight is off
        GPIO.output(BACKLIGHT_PIN, GPIO.HIGH)
        GPIO.cleanup()
        print("\nGPIO cleanup complete.")

if __name__ == '__main__':
    gpio_test()