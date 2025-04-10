"""HeySalad ESP32-S3 Food Recognition System.

Comprehensive motion-triggered image capture and AI analysis.
"""

import os
import board
import displayio
import time
import gc
import busio
import gc9a01
import espcamera
import microcontroller
import binascii
import digitalio

# Optional imports with graceful fallback
try:
    import wifi
    import socketpool
    import ssl
    import adafruit_requests
    WIFI_AVAILABLE = True
except ImportError:
    WIFI_AVAILABLE = False
    print("WiFi libraries not available")

# BLE imports
try:
    from adafruit_ble import BLERadio
    from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
    from adafruit_ble.services.nordic import UARTService
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False
    print("BLE libraries not available")


class Configuration:
    """Configuration constants for the HeySalad system."""

    # BLE Communication
    BLE_SERVICE_UUID = "de8a5aac-a99b-c315-0c80-60d4cbb51224"
    MG24_DEVICE_NAME = "HEYSALAD_MOTION"

    # Sensor Communication
    MOTION_DATA_DELIMITER = ","
    UART_BAUD_RATE = 115200

    # WiFi Networks
    WIFI_NETWORKS = [
        {"ssid": "iPhone von Chilu", "password": "123456789"},
        {"ssid": "HeySalad_02", "password": "GutenTag%800"},
        {"ssid": "VM7464351", "password": "zpijfcisoFw6cveh"}
    ]

    # Image Paths
    STANDARD_IMAGE = "HSK-STANDARD.bmp"
    PROCESSING_IMAGE = "HSK-SPEEDY.bmp"
    RESULT_IMAGE = "HSK-SHOCKED.bmp"


class HeySaladController:
    """Primary controller for the HeySalad food recognition system."""

    def __init__(self):
        """Initialize the HeySalad controller."""
        # Display initialization
        self._initialize_display()
        
        # Hardware components
        self._initialize_camera()
        self._initialize_wifi()
        self._initialize_ble()

    def _initialize_display(self):
        """Initialize the round GC9A01 display with robust error handling."""
        try:
            # Release displays to prevent conflicts
            displayio.release_displays()

            # SPI bus setup
            spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
            display_bus = displayio.FourWire(
                spi, 
                command=board.D3, 
                chip_select=board.D1
            )

            # Create display
            self._display = gc9a01.GC9A01(
                display_bus, 
                width=240, 
                height=240
            )

            # Create display group
            self._main_group = displayio.Group()
            self._display.root_group = self._main_group

            # Load startup image
            self._load_standard_image()

            print("Display initialized successfully")
        except Exception as e:
            print(f"Display initialization error: {e}")
            self._display = None
            self._main_group = None

    def _load_standard_image(self):
        """Load the standard startup image with comprehensive error handling."""
        try:
            # Clear existing group
            while len(self._main_group) > 0:
                self._main_group.pop()

            # Verify file exists
            if not os.path.exists(Configuration.STANDARD_IMAGE):
                print(f"Standard image not found: {Configuration.STANDARD_IMAGE}")
                self._display_fallback_color()
                return

            # Open and load bitmap
            with open(Configuration.STANDARD_IMAGE, "rb") as image_file:
                bitmap = displayio.OnDiskBitmap(image_file)
                tile_grid = displayio.TileGrid(
                    bitmap, 
                    pixel_shader=displayio.ColorConverter()
                )
                self._main_group.append(tile_grid)
            
            print(f"Standard image loaded: {Configuration.STANDARD_IMAGE}")
        
        except Exception as e:
            print(f"Error loading standard image: {e}")
            self._display_fallback_color()

    def _display_fallback_color(self):
        """Display a green fallback color when image loading fails."""
        color_bitmap = displayio.Bitmap(240, 240, 1)
        color_palette = displayio.Palette(1)
        color_palette[0] = 0x00FF00  # Green
        
        bg_sprite = displayio.TileGrid(
            color_bitmap, 
            pixel_shader=color_palette
        )
        self._main_group.append(bg_sprite)
        print("Using green fallback color")

    def _initialize_camera(self):
        """Initialize the ESP32-S3 camera with detailed error handling."""
        try:
            # Camera I2C setup
            cam_i2c = busio.I2C(board.CAM_SCL, board.CAM_SDA)

            # Camera configuration
            self._camera = espcamera.Camera(
                data_pins=board.CAM_DATA,
                external_clock_pin=board.CAM_XCLK,
                pixel_clock_pin=board.CAM_PCLK,
                vsync_pin=board.CAM_VSYNC,
                href_pin=board.CAM_HREF,
                pixel_format=espcamera.PixelFormat.JPEG,
                frame_size=espcamera.FrameSize.SVGA,
                i2c=cam_i2c,
                external_clock_frequency=20_000_000,
                framebuffer_count=2,
                grab_mode=espcamera.GrabMode.WHEN_EMPTY,
                jpeg_quality=10
            )
            print("Camera initialized successfully")
        except Exception as e:
            print(f"Camera initialization error: {e}")
            self._camera = None

    def _initialize_wifi(self):
        """Connect to WiFi with robust error handling."""
        if not WIFI_AVAILABLE:
            print("WiFi libraries not available")
            return

        for network in Configuration.WIFI_NETWORKS:
            try:
                print(f"Attempting to connect to '{network['ssid']}'...")
                wifi.radio.connect(network['ssid'], network['password'])
                
                # Create network resources
                self._socket_pool = socketpool.SocketPool(wifi.radio)
                self._ssl_context = ssl.create_default_context()
                self._requests = adafruit_requests.Session(
                    self._socket_pool, 
                    self._ssl_context
                )
                
                print(f"Connected to {network['ssid']}")
                return
            except Exception as e:
                print(f"Failed to connect to '{network['ssid']}': {e}")
        
        print("Could not connect to any WiFi network")

    def _initialize_ble(self):
        """Initialize Bluetooth Low Energy for MG24 communication."""
        if not BLE_AVAILABLE:
            print("BLE not available")
            return

        try:
            self._ble_radio = BLERadio()
            self._uart_service = UARTService()
            
            # Advertising setup
            advertisement = ProvideServicesAdvertisement(self._uart_service)
            self._ble_radio.start_advertising(advertisement)
            
            print("BLE initialized")
        except Exception as e:
            print(f"BLE initialization error: {e}")
            self._ble_radio = None
            self._uart_service = None

    def _process_ble_messages(self):
        """Process incoming BLE messages from MG24."""
        if not self._ble_radio or not self._uart_service:
            return

        try:
            # Check for available data
            if self._uart_service.in_waiting:
                message = self._uart_service.read(
                    self._uart_service.in_waiting
                ).decode('utf-8').strip()
                
                # Print received message for debugging
                print(f"Received BLE message: {message}")
                
                # Process motion data
                if Configuration.MOTION_DATA_DELIMITER in message:
                    self._process_motion_data(message)
                
                # Process commands
                if message == "GESTURE_CAPTURE":
                    print("Capture gesture detected")
                elif message == "GESTURE_RECIPE":
                    print("Recipe gesture detected")
                elif message == "START_CAMERA":
                    self._start_camera()
                elif message == "STOP_CAMERA":
                    self._stop_camera()
        except Exception as e:
            print(f"BLE message processing error: {e}")

    def _process_motion_data(self, data_str):
        """Process and log motion sensor data.

        Args:
            data_str: Comma-separated motion data string.
        """
        try:
            # Split motion data
            motion_values = data_str.split(Configuration.MOTION_DATA_DELIMITER)
            
            # Validate data
            if len(motion_values) >= 3:
                x, y, z = map(float, motion_values[:3])
                print(f"Motion Data - X: {x}, Y: {y}, Z: {z}")
        except Exception as e:
            print(f"Motion data processing error: {e}")

    def _start_camera(self):
        """Start the camera for image capture."""
        if self._camera:
            print("Starting camera")
            self._camera.enable()

    def _stop_camera(self):
        """Stop the camera."""
        if self._camera:
            print("Stopping camera")
            self._camera.disable()

    def run(self):
        """Main application event loop."""
        while True:
            try:
                # Process BLE messages
                self._process_ble_messages()
                
                # Periodic garbage collection
                if int(time.monotonic()) % 10 == 0:
                    gc.collect()
                
                time.sleep(0.1)
            
            except Exception as e:
                print(f"System error: {e}")
                time.sleep(1)


def main():
    """Entry point for the HeySalad application."""
    try:
        controller = HeySaladController()
        controller.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        time.sleep(5)
        microcontroller.reset()


# Application entry point
if __name__ == "__main__":
    main()