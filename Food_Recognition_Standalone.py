"""
HeySalad Food Recognition System for ESP32-S3 (Standalone Mode)

- Multiple WiFi network support
- Captures images using built-in camera
- Shows different tomato faces on round screen
- Simulates nutritional information about food

Three display states:
- Standard image (HSK-STANDARD.bmp) - default state
- Speedy image (HSK-SPEEDY.bmp) - processing state
- Shocked image (HSK-SHOCKED.bmp) - results/error state
"""
import board
import displayio
import time
import gc
import busio
import gc9a01
import espcamera
from displayio import release_displays
import random
import microcontroller
import digitalio

# Optional imports - try them but continue if not available
try:
    import wifi
    import socketpool
    import ssl
    import adafruit_requests
    WIFI_AVAILABLE = True
except ImportError:
    WIFI_AVAILABLE = False
    print("WiFi libraries not available")

try:
    import binascii
    BINASCII_AVAILABLE = True
except ImportError:
    BINASCII_AVAILABLE = False
    print("binascii library not available")

try:
    from adafruit_ble import BLERadio
    from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
    from adafruit_ble.uuid import UUID
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False
    print("BLE libraries not available")

# Release any resources currently in use for the displays
release_displays()

# WiFi Networks - multiple options for redundancy
WIFI_NETWORKS = [
    {"ssid": "iPhone von Chilu", "password": "123456789"},
    {"ssid": "HeySalad_02", "password": "GutenTag%800"},
    {"ssid": "VM7464351", "password": "zpijfcisoFw6cveh"}
]

# Image paths for different states
STANDARD_IMAGE = "HSK-STANDARD.bmp"
SPEEDY_IMAGE = "HSK-SPEEDY.bmp"
SHOCKED_IMAGE = "HSK-SHOCKED.bmp"

# Application states
STATE_IDLE = 0
STATE_CAPTURING = 1
STATE_PROCESSING = 2
STATE_DISPLAY_RESULTS = 3
STATE_ERROR = 4

# Define a button for capturing images
CAPTURE_BUTTON_PIN = board.D0  # Adjust this to match your button pin

class HeySaladApp:
    def __init__(self):
        print("Initializing HeySalad App...")
        print(f"Memory before init: {gc.mem_free()} bytes")
        
        # Initialize state
        self.current_state = STATE_IDLE
        self.nutritional_data = None
        self.error_message = None
        self.frame_offset_x = 0
        self.frame_offset_y = 0
        
        # Initialize hardware components
        self.init_display()
        self.init_camera()
        self.init_button()
        self.init_ble()  # Optional - will work without BLE
        
        # Try to connect to WiFi
        if WIFI_AVAILABLE:
            self.init_wifi()
        else:
            self.requests = None
        
        # BLE variables
        self.heysalad_service = None
        self.last_command_time = time.monotonic()
        
        print(f"Memory after init: {gc.mem_free()} bytes")
        print("HeySalad App initialized")
        
        # Show standard image on startup
        self.load_image(STANDARD_IMAGE)
        
    def init_display(self):
        """Initialize the round GC9A01 display"""
        try:
            print("Initializing display...")
            spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
            
            try:
                from fourwire import FourWire
            except ImportError:
                from displayio import FourWire
                
            display_bus = FourWire(spi, command=board.D3, chip_select=board.D1)
            self.display = gc9a01.GC9A01(display_bus, width=240, height=240)
            
            # Create main display group
            self.main_group = displayio.Group()
            self.display.root_group = self.main_group
            
            print("Display initialized successfully")
        except Exception as e:
            print(f"Display initialization error: {e}")
            self.display = None
            self.main_group = None
    
    def init_camera(self):
        """Initialize the ESP32-S3 camera"""
        try:
            print("Setting up camera...")
            cam_i2c = busio.I2C(board.CAM_SCL, board.CAM_SDA)
            
            self.camera = espcamera.Camera(
                data_pins=board.CAM_DATA,
                external_clock_pin=board.CAM_XCLK,
                pixel_clock_pin=board.CAM_PCLK,
                vsync_pin=board.CAM_VSYNC,
                href_pin=board.CAM_HREF,
                pixel_format=espcamera.PixelFormat.RGB565,
                frame_size=espcamera.FrameSize.SVGA,
                i2c=cam_i2c,
                external_clock_frequency=20_000_000,
                framebuffer_count=2,
                grab_mode=espcamera.GrabMode.WHEN_EMPTY
            )
            print("Camera initialized successfully")
        except Exception as e:
            print(f"Camera initialization error: {e}")
            self.camera = None
    
    def init_button(self):
        """Initialize a physical button for image capture"""
        try:
            self.button = digitalio.DigitalInOut(CAPTURE_BUTTON_PIN)
            self.button.direction = digitalio.Direction.INPUT
            self.button.pull = digitalio.Pull.UP  # Pulled up, button connects to ground
            self.button_state = self.button.value
            print("Button initialized successfully")
        except Exception as e:
            print(f"Button initialization error: {e}")
            self.button = None
            self.button_state = True  # Default to not pressed
    
    def init_ble(self):
        """Initialize BLE to connect to MG24 controller"""
        self.ble = None
        if not BLE_AVAILABLE:
            print("BLE libraries not available, BLE features will be disabled")
            return
            
        try:
            print("Initializing BLE...")
            self.ble = BLERadio()
            print("BLE initialized")
        except Exception as e:
            print(f"BLE initialization error: {e}")
            self.ble = None
    
    def init_wifi(self):
        """Connect to WiFi network - try multiple networks"""
        self.requests = None
        if not WIFI_AVAILABLE:
            return
            
        print("Attempting to connect to WiFi...")
        connected = False
        
        for network in WIFI_NETWORKS:
            try:
                print(f"Trying to connect to '{network['ssid']}'...")
                wifi.radio.connect(network['ssid'], network['password'])
                
                # If we get here, connection was successful
                print(f"Connected to '{network['ssid']}'")
                connected = True
                
                # Set up the request session
                self.pool = socketpool.SocketPool(wifi.radio)
                self.ssl_context = ssl.create_default_context()
                self.requests = adafruit_requests.Session(self.pool, self.ssl_context)
                
                print(f"IP address: {wifi.radio.ipv4_address}")
                break  # Exit the loop if we connect successfully
                
            except Exception as e:
                print(f"Failed to connect to '{network['ssid']}': {e}")
        
        if not connected:
            print("Could not connect to any WiFi network")
            self.requests = None
    
    def load_image(self, image_path):
        """Load an image to the display"""
        try:
            print(f"Loading image: {image_path}")
            # Clear the main group
            while len(self.main_group) > 0:
                self.main_group.pop()
            
            # Load the BMP file
            try:
                image_file = open(image_path, "rb")
                bitmap = displayio.OnDiskBitmap(image_file)
                tile_grid = displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter())
                
                # Add the TileGrid to the Group
                self.main_group.append(tile_grid)
                print(f"Image loaded: {image_path}")
            except OSError as e:
                print(f"Image file not found: {e}")
                # Create a colored background as fallback
                color_bitmap = displayio.Bitmap(240, 240, 1)
                color_palette = displayio.Palette(1)
                if image_path == STANDARD_IMAGE:
                    color_palette[0] = 0x00FF00  # Green
                elif image_path == SPEEDY_IMAGE:
                    color_palette[0] = 0xFFFF00  # Yellow
                else:
                    color_palette[0] = 0xFF0000  # Red
                bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette)
                self.main_group.append(bg_sprite)
                print("Using fallback colored background")
                
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
    
    def display_text(self, text):
        """Display text on the round screen"""
        try:
            print(f"Displaying text: {text[:30]}...")
            # Clear the main group
            while len(self.main_group) > 0:
                self.main_group.pop()
            
            # Create a simple colored background
            color_bitmap = displayio.Bitmap(240, 240, 1)
            color_palette = displayio.Palette(1)
            color_palette[0] = 0x000000  # Black background
            bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette)
            self.main_group.append(bg_sprite)
            
            # Print to console since we can't easily do text rendering
            print("----- NUTRITIONAL INFO -----")
            print(text)
            print("----------------------------")
            
        except Exception as e:
            print(f"Error displaying text: {e}")
    
    def check_button(self):
        """Check if the button was pressed (with debouncing)"""
        if not self.button:
            return False
            
        current_value = self.button.value
        
        # Check for button press (transition from high to low for pull-up configuration)
        if current_value == False and self.button_state == True:
            # Button just pressed
            self.button_state = False
            time.sleep(0.05)  # Debounce
            return True
        elif current_value == True and self.button_state == False:
            # Button released
            self.button_state = True
        
        return False
    
    def capture_image(self):
        """Capture an image from the camera"""
        if not self.camera:
            print("Camera not initialized")
            return None
            
        try:
            print("Capturing image...")
            self.current_state = STATE_CAPTURING
            self.load_image(SPEEDY_IMAGE)
            
            # Wait a moment for the display to update
            time.sleep(0.5)
            
            # Capture frame
            frame = self.camera.take(1)
            
            if not frame:
                print("Failed to capture image")
                return None
                
            print("Image captured successfully")
            return frame
        except Exception as e:
            print(f"Image capture error: {e}")
            return None
    
    def process_mock_food_data(self):
        """Return mock nutritional data for testing"""
        # List of foods with nutritional data
        foods = [
            """
            Food Identified: Apple
            
            Nutritional Summary:
            - Calories: 95 kcal
            - Protein: 0.5g
            - Carbohydrates: 25g
            - Fiber: 4g
            - Sugar: 19g
            
            Health insights:
            - Good source of dietary fiber
            - Contains vitamin C and antioxidants
            - Low in calories, good for weight management
            """,
            """
            Food Identified: Banana
            
            Nutritional Summary:
            - Calories: 105 kcal
            - Protein: 1.3g
            - Carbohydrates: 27g
            - Fiber: 3.1g
            - Sugar: 14g
            
            Health insights:
            - Good source of potassium
            - Contains vitamin B6 and vitamin C
            - Natural energy booster
            """,
            """
            Food Identified: Avocado
            
            Nutritional Summary:
            - Calories: 240 kcal
            - Protein: 3g
            - Carbohydrates: 12g
            - Fiber: 10g
            - Fat: 22g (mostly healthy monounsaturated)
            
            Health insights:
            - Rich in heart-healthy monounsaturated fats
            - High in potassium and fiber
            - Contains folate, vitamin K, and vitamin E
            """,
            """
            Food Identified: Broccoli
            
            Nutritional Summary:
            - Calories: 55 kcal
            - Protein: 3.7g
            - Carbohydrates: 11g
            - Fiber: 5g
            - Sugar: 2.6g
            
            Health insights:
            - Excellent source of vitamin C and vitamin K
            - Contains antioxidants and anti-inflammatory compounds
            - High in fiber and relatively high in protein for a vegetable
            """
        ]
        
        # Return a random food
        return random.choice(foods)
    
    def process_food_image(self):
        """Capture image and process it to get nutritional information"""
        try:
            # Capture image
            frame = self.capture_image()
            if not frame:
                self.error_message = "Failed to capture image"
                self.current_state = STATE_ERROR
                self.load_image(SHOCKED_IMAGE)
                return
            
            # Show processing screen
            self.load_image(SPEEDY_IMAGE)
            print("Processing image (simulated)...")
            time.sleep(2)  # Simulate processing time
            
            # Use mock data for testing
            nutritional_info = self.process_mock_food_data()
            
            if nutritional_info:
                # Process was successful
                self.nutritional_data = nutritional_info
                self.current_state = STATE_DISPLAY_RESULTS
                
                # Display nutritional results
                self.display_text(nutritional_info)
                
                # After 10 seconds, show shocked face
                time.sleep(10)
                self.load_image(SHOCKED_IMAGE)
                time.sleep(3)
                self.load_image(STANDARD_IMAGE)
                self.current_state = STATE_IDLE
            else:
                # Process failed
                self.error_message = "Failed to get nutritional information"
                self.current_state = STATE_ERROR
                self.load_image(SHOCKED_IMAGE)
                time.sleep(3)
                self.load_image(STANDARD_IMAGE)
                self.current_state = STATE_IDLE
                
        except Exception as e:
            print(f"Food processing error: {e}")
            self.error_message = f"Error: {str(e)}"
            self.current_state = STATE_ERROR
            self.load_image(SHOCKED_IMAGE)
            time.sleep(3)
            self.load_image(STANDARD_IMAGE)
            self.current_state = STATE_IDLE
    
    def run(self):
        """Main application loop"""
        print("Starting HeySalad app main loop...")
        
        # Start with standard image
        self.load_image(STANDARD_IMAGE)
        last_button_check = time.monotonic()
        
        while True:
            try:
                # Check for button press to trigger image capture
                if self.current_state == STATE_IDLE:
                    if self.check_button():
                        print("Button pressed - capturing image")
                        self.process_food_image()
                
                # Run garbage collection periodically
                if int(time.monotonic()) % 10 == 0:
                    gc.collect()
                
                # Small delay to prevent tight loop
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

# Run the application
if __name__ == "__main__":
    try:
        app = HeySaladApp()
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        time.sleep(5)