"""
Camera Frame at Round Display (GC9A01) using direct display commands
"""
import board
import busio
import displayio
import espcamera
import adafruit_ticks
import gc9a01
import time
import gc
import struct

# Release any resources currently in use for the displays
displayio.release_displays()
print("Memory before:", gc.mem_free())

# Use the pin configuration from your working example
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

# Initialize SPI bus
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
display_bus = FourWire(spi, command=board.D3, chip_select=board.D1)

# Create the GC9A01 display with 240x240 resolution
display = gc9a01.GC9A01(display_bus, width=240, height=240, rotation=0)
print("Display initialized successfully")

# Camera I2C setup
print("Setting up camera...")
cam_i2c = busio.I2C(board.CAM_SCL, board.CAM_SDA)

# Camera initialization
cam = espcamera.Camera(
    data_pins=board.CAM_DATA,
    external_clock_pin=board.CAM_XCLK,
    pixel_clock_pin=board.CAM_PCLK,
    vsync_pin=board.CAM_VSYNC,
    href_pin=board.CAM_HREF,
    pixel_format=espcamera.PixelFormat.RGB565,
    frame_size=espcamera.FrameSize.R240X240,
    i2c=cam_i2c,
    external_clock_frequency=20_000_000,
    framebuffer_count=2,
    grab_mode=espcamera.GrabMode.WHEN_EMPTY
)

print("Camera initialized successfully")
print("Memory after camera setup:", gc.mem_free())

# Disable auto refresh - we'll handle display updates manually
display.auto_refresh = False

# GC9A01 display commands
CASET = 0x2A  # Column Address Set
RASET = 0x2B  # Row Address Set
RAMWR = 0x2C  # Memory Write

print("Starting camera capture...")
t0 = adafruit_ticks.ticks_ms()
frame_count = 0

while True:
    try:
        # Grab a frame from the camera
        frame = cam.take(1)
        
        if frame:
            # Set the address window for the entire display
            # This tells the display where to put the pixel data
            display_bus.send(CASET, struct.pack(">HH", 0, 239))  # Column start/end
            display_bus.send(RASET, struct.pack(">HH", 0, 239))  # Row start/end
            
            # Send the camera frame directly to the display
            display_bus.send(RAMWR, frame)
            
            # Calculate FPS every 10 frames
            frame_count += 1
            if frame_count >= 10:
                t1 = adafruit_ticks.ticks_ms()
                fps = 10000 / adafruit_ticks.ticks_diff(t1, t0)
                print(f"{fps:3.1f}fps")
                t0 = t1
                frame_count = 0
                
                # Print memory usage occasionally
                print(f"Memory: {gc.mem_free()} bytes free")
        else:
            print("No valid frame")
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Error in camera loop: {e}")
        time.sleep(1)