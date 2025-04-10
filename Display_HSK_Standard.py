# Save this as code.py on your device - this is a minimal test that *only* displays an image
import board
import displayio
import time
import gc
from displayio import release_displays

# Release any resources currently in use for the displays
release_displays()

print("Memory before:", gc.mem_free())

try:
    # Create the main display group
    main_group = displayio.Group()
    
    # Load the BMP file in the simplest possible way
    print("Loading image...")
    image_file = open("HSK-STANDARD.bmp", "rb")
    bitmap = displayio.OnDiskBitmap(image_file)
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter())
    
    # Add the TileGrid to the Group
    main_group.append(tile_grid)
    
    # Create the display
    import gc9a01
    import busio
    spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
    
    try:
        from fourwire import FourWire
    except ImportError:
        from displayio import FourWire
        
    display_bus = FourWire(spi, command=board.D3, chip_select=board.D1)
    display = gc9a01.GC9A01(display_bus, width=240, height=240)
    
    # Show the image using root_group instead of show()
    display.root_group = main_group
    
    print("Image should be displayed now")
    print("Memory after:", gc.mem_free())

except Exception as e:
    print(f"Error: {e}")

# Keep the program running
while True:
    time.sleep(1)