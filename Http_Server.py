"""
HeySalad Camera Server for ESP32-S3 with GC9A01 Display (Fixed Version)

Features:
- Built-in HTTP server for camera streaming and control
- Camera display on local GC9A01 round display
- WebSocket support for live streaming
- Serves a web interface for viewing the camera feed
"""
import board
import busio
import displayio
import espcamera
import time
import gc
import struct
import json
import binascii
import socketpool
import wifi
import microcontroller
from displayio import release_displays

# HTTP Server and WebSocket libraries
from adafruit_httpserver import Server, Request, Response, Websocket, GET

# Display-related imports
import gc9a01
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

# Release any resources currently in use for the displays
release_displays()
print(f"Memory before init: {gc.mem_free()} bytes")

# WiFi Networks - multiple options for redundancy
WIFI_NETWORKS = [
    {"ssid": "HeySalad_02", "password": "GutenTag%800"},
    {"ssid": "iPhone von Chilu", "password": "123456789"},
    {"ssid": "VM7464351", "password": "zpijfcisoFw6cveh"}
]

# Image paths for different states
STANDARD_IMAGE = "HSK-STANDARD.bmp"
SPEEDY_IMAGE = "HSK-SPEEDY.bmp"
SHOCKED_IMAGE = "HSK-SHOCKED.bmp"

# Application states
STATE_IDLE = 0
STATE_STREAMING = 1
STATE_ERROR = 2

# HTML for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HeySalad Camera Stream</title>
    <style>
        :root {
            --primary-color: #ed4c4c; /* Cherry Red */
            --secondary-color: #faa09a; /* Peach */
            --tertiary-color: #ffd0cd; /* Light Peach */
            --bg-color: #ffffff; /* White */
            --card-color: #FFFFFF;
            --text-color: #333333;
            --error-color: #ed4c4c; /* Using Cherry Red for errors too */
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .container {
            max-width: 360px;
            width: 95%;
            margin: 20px auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 20px;
        }
        
        h1 {
            color: var(--primary-color);
        }
        
        .logo-container {
            display: flex;
            justify-content: center;
            margin-bottom: 15px;
        }
        
        .logo {
            width: 100px;
            height: 100px;
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
        }
        
        .stream-container {
            position: relative;
            width: 100%;
            max-width: 300px;
            height: 0;
            padding-bottom: 100%;
            background-color: #000;
            border-radius: 50%;
            overflow: hidden;
            margin: 0 auto;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }
        
        #camera-feed {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
            background-color: var(--tertiary-color);
            color: var(--primary-color);
            font-weight: bold;
        }
        
        .status.connected {
            background-color: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
        }
        
        .status.disconnected {
            background-color: rgba(244, 67, 54, 0.2);
            color: var(--error-color);
        }
        
        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
        }
        
        .btn {
            background-color: var(--tertiary-color);
            color: var(--primary-color);
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .btn svg {
            width: 30px;
            height: 30px;
            fill: currentColor;
        }
        
        .btn:hover {
            background-color: var(--secondary-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .btn.primary {
            background-color: var(--primary-color);
            color: white;
        }
        
        .btn.primary:hover {
            background-color: var(--secondary-color);
        }
        
        .btn.active {
            background-color: var(--secondary-color);
            border: 2px solid var(--primary-color);
            transform: scale(1.05);
        }
        
        .info-panel {
            background-color: var(--card-color);
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            max-width: 300px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .info-panel h3 {
            margin-top: 0;
            color: var(--primary-color);
        }
        
        #cpu-temp {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-container">
                <div class="logo" id="heysalad-logo"></div>
            </div>
            <h1>HeySalad<sup>®</sup> Camera Stream</h1>
            <p>Live stream from ESP32-S3 with GC9A01 round display</p>
        </header>
        
        <div class="stream-container">
            <canvas id="camera-feed" width="240" height="240"></canvas>
        </div>
        
        <div id="connection-status" class="status">Connecting to websocket...</div>
        
        <div class="controls">
            <button id="start-stream-btn" class="btn primary">
                <svg viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            </button>
            <button id="stop-stream-btn" class="btn">
                <svg viewBox="0 0 24 24">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                </svg>
            </button>
            <button id="refresh-btn" class="btn">
                <svg viewBox="0 0 24 24">
                    <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 9h7V2l-2.35 4.35z"/>
                </svg>
            </button>
        </div>
        
        <div class="info-panel">
            <h3>Device Information</h3>
            <p>CPU Temperature: <span id="cpu-temp">-</span>°C</p>
            <p>Memory Available: <span id="memory-available">-</span> bytes</p>
        </div>
    </div>

    <script>
        // DOM elements
        const canvas = document.getElementById('camera-feed');
        const ctx = canvas.getContext('2d');
        const statusEl = document.getElementById('connection-status');
        const cpuTempEl = document.getElementById('cpu-temp');
        const memoryEl = document.getElementById('memory-available');
        const refreshBtn = document.getElementById('refresh-btn');
        const startStreamBtn = document.getElementById('start-stream-btn');
        const stopStreamBtn = document.getElementById('stop-stream-btn');
        const heySaladLogo = document.getElementById('heysalad-logo');
        
        // WebSocket variables
        let ws = null;
        let connected = false;
        let reconnectAttempts = 0;
        const MAX_RECONNECT_ATTEMPTS = 5;
        
        // Set logo background
        // We'll use the BMP logo for simplicity
        fetch('/logo')
            .then(response => response.json())
            .then(data => {
                if (data && data.image) {
                    heySaladLogo.style.backgroundImage = `url(data:image/jpeg;base64,${data.image})`;
                }
            })
            .catch(error => {
                console.error('Failed to load logo:', error);
                // Use a color as fallback
                heySaladLogo.style.backgroundColor = 'var(--primary-color)';
            });
        
        // Connect to WebSocket
        function connectWebSocket() {
            // Close existing connection if any
            if (ws) {
                ws.close();
            }
            
            // Update status
            statusEl.className = 'status';
            statusEl.textContent = 'Connecting to websocket...';
            
            // Create new WebSocket connection
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            // WebSocket event handlers
            ws.onopen = () => {
                connected = true;
                reconnectAttempts = 0;
                statusEl.className = 'status connected';
                statusEl.textContent = 'Connected to camera stream';
                
                // Check streaming status on connect
                fetchStreamingStatus();
            };
            
            ws.onclose = () => {
                connected = false;
                statusEl.className = 'status disconnected';
                statusEl.textContent = 'Disconnected from camera stream';
                
                // Attempt to reconnect
                if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    reconnectAttempts++;
                    setTimeout(connectWebSocket, 3000);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                statusEl.className = 'status disconnected';
                statusEl.textContent = 'Connection error';
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    // Handle different message types
                    if (data.type === 'frame') {
                        // Handle camera frame
                        drawFrame(data.width, data.height, data.format, data.data);
                    } else if (data.type === 'info') {
                        // Update device information
                        if (data.cpu_temp) {
                            cpuTempEl.textContent = data.cpu_temp.toFixed(1);
                        }
                        if (data.memory) {
                            memoryEl.textContent = data.memory;
                        }
                        
                        // Update streaming status buttons
                        updateStreamingButtons(data.streaming);
                    } else if (data.type === 'command_response') {
                        console.log('Command response:', data);
                        
                        // Update streaming status buttons based on response
                        if (data.streaming !== undefined) {
                            updateStreamingButtons(data.streaming);
                        }
                    }
                } catch (error) {
                    console.error('Error processing message:', error);
                }
            };
        }
        
        function updateStreamingButtons(isStreaming) {
            if (isStreaming) {
                startStreamBtn.classList.add('active');
                stopStreamBtn.classList.remove('active');
            } else {
                startStreamBtn.classList.remove('active');
                stopStreamBtn.classList.add('active');
            }
        }
        
        // Fetch streaming status from server
        function fetchStreamingStatus() {
            fetch('/info')
                .then(response => response.json())
                .then(data => {
                    updateStreamingButtons(data.streaming);
                    
                    // Update other info
                    if (data.cpu_temp) {
                        cpuTempEl.textContent = data.cpu_temp.toFixed(1);
                    }
                    if (data.memory) {
                        memoryEl.textContent = data.memory;
                    }
                })
                .catch(error => {
                    console.error('Error fetching streaming status:', error);
                });
        }
        
        // Draw frame on canvas
        function drawFrame(width, height, format, data) {
            if (format === 'rgb565') {
                // Convert binary RGB565 data to ImageData
                const imageData = new ImageData(width, height);
                const buffer = new Uint8Array(width * height * 4); // RGBA
                
                const binary = atob(data); // Base64 decode
                
                // Convert RGB565 to RGBA
                for (let i = 0; i < binary.length; i += 2) {
                    const idx = i / 2;
                    const pixelVal = (binary.charCodeAt(i) << 8) | binary.charCodeAt(i + 1);
                    
                    // RGB565: RRRRRGGG GGGBBBBB
                    const r = ((pixelVal >> 11) & 0x1F) << 3;
                    const g = ((pixelVal >> 5) & 0x3F) << 2;
                    const b = (pixelVal & 0x1F) << 3;
                    
                    const rgbaIdx = idx * 4;
                    buffer[rgbaIdx] = r;
                    buffer[rgbaIdx + 1] = g;
                    buffer[rgbaIdx + 2] = b;
                    buffer[rgbaIdx + 3] = 255; // Alpha
                }
                
                imageData.data.set(buffer);
                ctx.putImageData(imageData, 0, 0);
            }
        }
        
        // Event listeners
        refreshBtn.addEventListener('click', () => {
            connectWebSocket();
        });
        
        startStreamBtn.addEventListener('click', () => {
            console.log("Start stream button clicked");
            
            // Send command to start streaming
            if (ws && connected) {
                ws.send(JSON.stringify({ command: 'start_stream' }));
            } else {
                connectWebSocket();
                setTimeout(() => {
                    if (ws && connected) {
                        ws.send(JSON.stringify({ command: 'start_stream' }));
                    }
                }, 1000);
            }
        });
        
        stopStreamBtn.addEventListener('click', () => {
            console.log("Stop stream button clicked");
            
            // Send command to stop streaming
            if (ws && connected) {
                ws.send(JSON.stringify({ command: 'stop_stream' }));
            }
        });
        
        // Reconnect WebSocket when window gains focus
        window.addEventListener('focus', () => {
            if (!connected) {
                connectWebSocket();
            }
        });
        
        // Initialize connection
        connectWebSocket();
    </script>
</body>
</html>
"""

class CameraWebServer:
    def __init__(self):
        """Initialize the camera web server application"""
        print("Initializing HeySalad Camera Web Server...")
        
        # Initialize state
        self.current_state = STATE_IDLE
        self.error_message = None
        self.active_websockets = set()
        self.last_frame_time = time.monotonic()
        self.frame_interval = 0.1  # 10 FPS
        self.streaming_enabled = False  # Start with streaming disabled to save power
        
        # Initialize hardware components
        self.init_display()
        self.init_camera()
        
        # Try to connect to WiFi and set up the server
        self.init_wifi()
        
        # Show standard image on startup
        self.load_image(STANDARD_IMAGE)
        print(f"Memory after init: {gc.mem_free()} bytes")
        print("HeySalad Camera Web Server initialized")
    
    def init_display(self):
        """Initialize the round GC9A01 display"""
        try:
            print("Initializing display...")
            # Initialize SPI bus
            spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
            display_bus = FourWire(spi, command=board.D3, chip_select=board.D1)
            
            # Create the GC9A01 display with 240x240 resolution
            self.display = gc9a01.GC9A01(display_bus, width=240, height=240)
            
            # Create main display group
            self.main_group = displayio.Group()
            self.display.root_group = self.main_group
            
            # GC9A01 display commands for direct frame updates
            self.CASET = 0x2A  # Column Address Set
            self.RASET = 0x2B  # Row Address Set
            self.RAMWR = 0x2C  # Memory Write
            self.display_bus = display_bus
            
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
                frame_size=espcamera.FrameSize.R240X240,  # Using 240x240 for the round display
                i2c=cam_i2c,
                external_clock_frequency=20_000_000,
                framebuffer_count=2,
                grab_mode=espcamera.GrabMode.WHEN_EMPTY
            )
            print("Camera initialized successfully")
        except Exception as e:
            print(f"Camera initialization error: {e}")
            self.camera = None
    
    def init_wifi(self):
        """Connect to WiFi network and set up the HTTP server"""
        print("Attempting to connect to WiFi...")
        connected = False
        
        for network in WIFI_NETWORKS:
            try:
                print(f"Trying to connect to '{network['ssid']}'...")
                wifi.radio.connect(network['ssid'], network['password'])
                
                # If we get here, connection was successful
                print(f"Connected to '{network['ssid']}'")
                connected = True
                print(f"IP address: {wifi.radio.ipv4_address}")
                
                # Initialize HTTP server
                self.init_server()
                break  # Exit the loop if we connect successfully
                
            except Exception as e:
                print(f"Failed to connect to '{network['ssid']}': {e}")
        
        if not connected:
            print("Could not connect to any WiFi network")
            self.show_error("WiFi connection failed")
    
    def init_server(self):
        """Initialize the HTTP server with routes"""
        try:
            print("Setting up HTTP server...")
            # Create socket pool
            self.pool = socketpool.SocketPool(wifi.radio)
            
            # Initialize server
            self.server = Server(self.pool, debug=True)
            
            # Configure routes
            @self.server.route("/")
            def index(request: Request):
                """Serve the main HTML page"""
                return Response(request, HTML_TEMPLATE, content_type="text/html")
            
            @self.server.route("/ws", GET)
            def websocket_handler(request: Request):
                """Handle WebSocket connections for streaming camera data"""
                try:
                    websocket = Websocket(request)
                    self.active_websockets.add(websocket)
                    print(f"New WebSocket client connected. Total: {len(self.active_websockets)}")
                    return websocket
                except Exception as e:
                    print(f"WebSocket connection error: {e}")
                    return Response(request, f"WebSocket error: {str(e)}", content_type="text/plain")
            
            @self.server.route("/info", GET)
            def info_handler(request: Request):
                """Return device information as JSON"""
                info = {
                    "cpu_temp": microcontroller.cpu.temperature,
                    "memory": gc.mem_free(),
                    "device": "ESP32-S3",
                    "version": "1.0",
                    "streaming": self.streaming_enabled
                }
                return Response(request, json.dumps(info), content_type="application/json")
            
            @self.server.route("/logo", GET)
            def logo_handler(request: Request):
                """Return the logo as base64 encoded image"""
                try:
                    # Just use the BMP for reliability
                    with open(SPEEDY_IMAGE, "rb") as f:
                        logo_data = f.read()
                    
                    # Convert to base64
                    logo_base64 = binascii.b2a_base64(logo_data).decode('ascii').strip()
                    
                    # Return as JSON
                    return Response(request, json.dumps({"image": logo_base64}), content_type="application/json")
                except Exception as e:
                    print(f"Error serving logo: {e}")
                    return Response(request, json.dumps({"error": str(e)}), content_type="application/json")
            
            # Start the server
            print(f"Starting server on http://{wifi.radio.ipv4_address}")
            self.server.start(str(wifi.radio.ipv4_address))
            self.current_state = STATE_STREAMING
            
            # Show success on display
            self.load_image(SPEEDY_IMAGE)
            time.sleep(1)
            self.load_image(STANDARD_IMAGE)
            
            print("HTTP server started successfully")
        except Exception as e:
            print(f"Server initialization error: {e}")
            self.server = None
            self.show_error(f"Server initialization failed: {e}")
    
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
    
    def show_error(self, message):
        """Display error state"""
        print(f"ERROR: {message}")
        self.current_state = STATE_ERROR
        self.error_message = message
        self.load_image(SHOCKED_IMAGE)
        time.sleep(3)  # Show error face for 3 seconds
        self.load_image(STANDARD_IMAGE)
        self.current_state = STATE_IDLE
    
    def direct_display_frame(self, frame):
        """Display camera frame directly to the display using low-level commands"""
        try:
            if self.display and self.display_bus:
                # Set the address window for the entire display
                self.display_bus.send(self.CASET, struct.pack(">HH", 0, 239))  # Column start/end
                self.display_bus.send(self.RASET, struct.pack(">HH", 0, 239))  # Row start/end
                
                # Send the camera frame directly to the display
                self.display_bus.send(self.RAMWR, frame)
                return True
            return False
        except Exception as e:
            print(f"Error displaying frame: {e}")
            return False
    
    def broadcast_to_websockets(self, message):
        """Send a message to all connected WebSocket clients"""
        # Create a copy of the set to avoid "Set changed size during iteration" errors
        websockets = set(self.active_websockets)
        closed_sockets = set()
        
        for websocket in websockets:
            try:
                websocket.send_message(message)
            except Exception as e:
                print(f"Error sending to websocket: {e}")
                # Mark this websocket for removal
                closed_sockets.add(websocket)
        
        # Remove closed websockets
        self.active_websockets -= closed_sockets
        
        # If any were removed, log it
        if closed_sockets:
            print(f"Removed {len(closed_sockets)} closed WebSocket connections. {len(self.active_websockets)} remaining.")
    
    def process_websocket_messages(self):
        """Process any incoming WebSocket messages"""
        # Make a copy to avoid modifying the set during iteration
        websockets = set(self.active_websockets)
        for websocket in websockets:
            try:
                message = websocket.receive(fail_silently=True)
                if message:
                    try:
                        print(f"Received WebSocket message: {message}")
                        data = json.loads(message)
                        
                        # Handle commands
                        if "command" in data:
                            command = data["command"]
                            
                            if command == "start_stream":
                                print("Starting camera stream")
                                self.streaming_enabled = True
                                self.load_image(SPEEDY_IMAGE)
                                
                                # Respond to the client
                                response = {
                                    "type": "command_response",
                                    "command": "start_stream",
                                    "success": True,
                                    "streaming": True
                                }
                                websocket.send_message(json.dumps(response))
                                
                            elif command == "stop_stream":
                                print("Stopping camera stream")
                                self.streaming_enabled = False
                                self.load_image(STANDARD_IMAGE)
                                
                                # Respond to the client
                                response = {
                                    "type": "command_response",
                                    "command": "stop_stream",
                                    "success": True,
                                    "streaming": False
                                }
                                websocket.send_message(json.dumps(response))
                                
                            else:
                                print(f"Unknown command: {command}")
                                # Respond with error
                                response = {
                                    "type": "error",
                                    "message": f"Unknown command: {command}"
                                }
                                websocket.send_message(json.dumps(response))
                                
                    except json.JSONDecodeError:
                        print(f"Invalid JSON in WebSocket message: {message}")
                    except Exception as e:
                        print(f"Error processing WebSocket message: {e}")
            except Exception as e:
                print(f"Error receiving from WebSocket: {e}")
    
    def capture_and_broadcast_frame(self):
        """Capture a frame and broadcast it to all connected clients"""
        if not self.camera or not self.streaming_enabled:
            return False
            
        try:
            # Only proceed if we have websocket clients
            if not self.active_websockets:
                return False
                
            # Capture frame
            frame = self.camera.take(1)
            
            if not frame:
                print("Failed to capture frame")
                return False
            
            # Display the frame locally on the round display
            self.direct_display_frame(frame)
            
            #
