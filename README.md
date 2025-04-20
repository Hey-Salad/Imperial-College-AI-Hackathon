# HeySalad® Food Recognition System with Kelly AI

<img src="https://raw.githubusercontent.com/Hey-Salad/.github/refs/heads/main/HeySalad%20Logo%20%2B%20Tagline%20Black.svg" alt="HeySalad Logo" width="400"/>

## About

HeySalad® is a smart food recognition device developed during the Imperial College AI Hackathon. The system combines an ESP32-S3 camera with a GC9A01 round display and AI-powered food recognition through our agent named Kelly. Special thanks to Ming and Mahe from Imperial College for their support and contributions to this project.

[Watch the behind-the-scenes video](https://www.youtube.com/watch?v=4rCXqwr4klM)

## Features

- **Kelly AI Agent**: Intelligent food recognition with nutritional information
- **Live Camera Streaming**: Real-time video feed to web browsers via WebSockets
- **GC9A01 Round Display**: Displays captured images and food information locally
- **Interactive UI**: Control streaming and camera functions through a web interface
- **Multiple WiFi Support**: Connects to various networks for reliable operation
- **Energy Management**: Start/stop controls to manage power consumption and CPU temperature

## Repository Contents

```
Imperial-College-AI-Hackathon/
├── BLE_Food_Recognition.py       # BLE communication for food recognition
├── Camera_Stream_Save_Memory.py  # Memory-optimized camera streaming
├── Display_HSK_Standard.py       # Display controller for standard mode
├── Food_Recognition_Standalone.py # Standalone food recognition implementation
├── HSK-SPEEDY.bmp                # Speedy mode display image (BMP)
├── HSK-SPEEDY.png                # Speedy mode display image (PNG)
├── HSK-STANDARD.bmp              # Standard mode display image (BMP)
├── HSK-STANDARD.png              # Standard mode display image (PNG)
├── HSKAI.ino                     # Arduino sketch for AI integration
├── Http_Server.py                # HTTP server implementation
├── README.md                     # This documentation
├── _HSK-SHOCKED.bmp              # Shocked mode display image (BMP)
├── _HSK-SHOCKED.png              # Shocked mode display image (PNG)
└── screenshots/                  # Project screenshots and documentation
```

## System Components

### Hardware

- **ESP32-S3**: Main controller with integrated camera module
- **GC9A01 Display**: 240x240 round display for visual feedback
- **Seeedstudio reCamera**: Optional integration for enhanced AI capabilities

### Software

- **Kelly AI Agent**: Our food recognition system built on machine learning
- **HTTP Server**: Serves the web interface using adafruit_httpserver
- **WebSocket Server**: Handles real-time camera streaming
- **Display Controller**: Manages the GC9A01 display output
- **WiFi Manager**: Handles network connectivity

## Web Interface

The web interface provides a user-friendly way to interact with the device:

- **Live Stream View**: Watch the camera feed in real-time
- **Control Buttons**: Play/pause streaming, refresh connection
- **Device Information**: Monitor CPU temperature and memory usage
- **Food Recognition Results**: View identified foods and nutritional information

## Getting Started

### Prerequisites

- CircuitPython 8.0+
- ESP32-S3 development board
- GC9A01 round display
- Camera module compatible with ESP32-S3

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/Hey-Salad/Imperial-College-AI-Hackathon.git
   ```

2. Install required CircuitPython libraries:
   - adafruit_httpserver
   - adafruit_gc9a01
   - adafruit_espcamera
   - displayio

3. Copy the code and image assets to your CircuitPython device

4. Configure WiFi networks in the code

5. Power up the device and connect to the web interface

## Using the Device

1. **Power On**: Connect power to the ESP32-S3
2. **Wait for Connection**: The device will connect to WiFi (display shows standard image)
3. **Find IP Address**: Check the serial console for the device's IP address
4. **Connect Web Interface**: Open a browser and navigate to the IP address
5. **Start Streaming**: Click the play button to begin camera streaming
6. **Identify Food**: Point the camera at food items to activate Kelly AI recognition
7. **View Results**: Nutritional information appears on both the web interface and display

## reCamera Integration

This project can optionally integrate with Seeedstudio's reCamera for enhanced AI performance:

- 1 TOPS@Int8 AI acceleration
- 5MP @ 30FPS video encoding
- YOLO11 native support
- Additional connectivity options

To use reCamera with this project, refer to our documentation on the [HeySalad reCamera Documentation](https://heysalad-io.notion.site/How-to-use-Seeedstudio-reCamera-Documentation-for-HeySalad-rs-1482409b5e7280b2b7c8e802a2ccab80).

## Implementation Details

### HTTP Server Code

The `Http_Server.py` file implements a web server that:
- Serves a responsive web interface
- Handles WebSocket connections for live streaming
- Processes commands to start/stop streaming
- Provides device information via API endpoints

### Display Controller

The display controller manages the GC9A01 round display:
- Shows different states using BMP images
- Directly displays camera frames in real-time
- Provides visual feedback for device status

### Food Recognition

Kelly AI processes camera images to identify food:
- Uses machine learning to recognize different food items
- Provides nutritional information for recognized foods
- Displays results on both the web interface and local display

## Screenshots

<img src="screenshots/Bildschirmfoto 2025-04-21 um 00.08.15.png" alt="Web Interface" width="600"/>

*Web interface showing the camera stream and controls*

<img src="screenshots/450C712D-AD2C-4916-A43D-FEAAEC038A1F 2.JPG" alt="Hardware Setup" width="600"/>

*Hardware setup with ESP32-S3 and GC9A01 display*

## Contributing

We welcome contributions to improve this project! Areas we're particularly interested in:

- Performance optimizations
- UI/UX improvements
- Food recognition accuracy enhancements
- Power management features

## Acknowledgments

Special thanks to:
- Ming and Mahe from Imperial College
- The CircuitPython community
- Adafruit for their excellent libraries
- Seeed Studio for the reCamera platform
- All participants of the Imperial College AI Hackathon

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For more information about HeySalad®:
- Website: [heysalad.io](https://heysalad.io)
- Email: peter@heysalad.io

---

Made with ❤️ by HeySalad®
