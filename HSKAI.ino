/**
 * HeySalad Motion and Audio Controller for XIAO MG24
 * 
 * Integrated motion and audio sensing system for food recognition.
 * Communicates with ESP32-S3 via BLE and UART.
 * 
 * @file heysalad_motion_controller.ino
 * @author Peter Machona
 * @date April 2025
 */

 #include <Arduino.h>
 #include <Wire.h>
 #include <LSM6DS3.h>
 #include <mic.h>
 
 // Namespace for configuration constants
 namespace heysalad {
 namespace config {
 
 // Debugging configuration
 constexpr bool kEnableDetailedLogging = true;
 
 // Communication settings
 constexpr int kSerialBaudRate = 115200;
 constexpr unsigned long kDataSendInterval = 200;  // milliseconds
 constexpr int kSerialTimeout = 1000;  // Serial read timeout in milliseconds
 
 // Logging function for debugging
 void LogDebug(const String& message) {
   if (kEnableDetailedLogging) {
     Serial.println("[DEBUG] " + message);
   }
 }
 
 // Logging function for errors
 void LogError(const String& message) {
   Serial.println("[ERROR] " + message);
 }
 
 // BLE Service and Characteristic UUIDs
 constexpr char* kServiceUuid = "de8a5aac-a99b-c315-0c80-60d4cbb51224";
 constexpr char* kAccelCharUuid = "5b026510-4088-c297-46d8-be6c736a087a";
 constexpr char* kEventCharUuid = "61a885a4-41c3-60d0-9a53-6d652a70d29c";
 constexpr char* kAudioCharUuid = "7c9e1a3f-2b5d-4f6a-9a1c-0d3e5f8a7b2c";
 
 // Audio recording configuration
 constexpr int kAudioSampleRate = 16000;
 constexpr int kAudioBufferSize = 16000 * 3;  // 3 seconds of audio
 
 // Motion detection thresholds
 constexpr float kCaptureGestureThreshold = 2.0f;
 constexpr float kRecipeGestureThreshold = 2.5f;
 constexpr float kGestureResetThreshold = 1.2f;
 
 }  // namespace config
 }  // namespace heysalad
 
 /**
  * Gesture types detected by the motion controller.
  */
 enum class GestureType {
   kNone = 0,
   kCaptureFood = 1,
   kViewRecipe = 2
 };
 
 /**
  * Primary motion and audio controller class for HeySalad system.
  */
 class HeySaladMotionController {
  public:
   /**
    * Initializes the motion controller hardware and interfaces.
    * 
    * @return bool True if initialization was successful, false otherwise.
    */
   bool Initialize() {
     // Initialize serial communication with extended timeout
     Serial.begin(heysalad::config::kSerialBaudRate);
     Serial.setTimeout(heysalad::config::kSerialTimeout);
     
     Serial1.begin(heysalad::config::kSerialBaudRate);
     Serial1.setTimeout(heysalad::config::kSerialTimeout);
 
     // Delay to ensure serial ports are fully initialized
     delay(500);
 
     // Log initialization start
     heysalad::config::LogDebug("Starting HeySalad Motion Controller Initialization");
 
     // Initialize hardware components with detailed error reporting
     if (!InitializeInertialMeasurementUnit()) {
       heysalad::config::LogError("IMU initialization failed");
       return false;
     }
 
     if (!InitializeMicrophone()) {
       heysalad::config::LogError("Microphone initialization failed");
       return false;
     }
 
     // Additional initialization diagnostic information
     heysalad::config::LogDebug("Serial Interfaces Configured");
     heysalad::config::LogDebug("Hardware Components Initialized");
     
     heysalad::config::LogDebug("HeySalad Motion Controller Fully Initialized");
     return true;
   }
 
   /**
    * Main processing loop for motion and audio detection.
    */
   void ProcessLoop() {
     UpdateSensorData();
     DetectGestures();
     ProcessCommands();
     SendPeriodicData();
   }
 
  private:
   // IMU and sensor variables
   LSM6DS3 imu_{I2C_MODE, 0x6A};
   float acceleration_x_ = 0.0f;
   float acceleration_y_ = 0.0f;
   float acceleration_z_ = 0.0f;
   float acceleration_magnitude_ = 0.0f;
 
   // Audio recording variables
   int16_t audio_buffer_[heysalad::config::kAudioBufferSize];
   volatile bool is_recording_ = false;
   volatile bool is_audio_ready_ = false;
 
   // Gesture detection variables
   int gesture_count_ = 0;
   bool gesture_detected_ = false;
 
   /**
    * Initializes the Inertial Measurement Unit.
    * 
    * @return bool True if IMU initialization was successful.
    */
   bool InitializeInertialMeasurementUnit() {
     heysalad::config::LogDebug("Attempting IMU Initialization");
     
     if (imu_.begin() != 0) {
       heysalad::config::LogError("IMU Begin Failed");
       return false;
     }
 
     // Configure IMU settings for precise gesture detection
     imu_.settings.accelRange = 8;        // ±8g range
     imu_.settings.gyroRange = 1000;      // ±1000dps rotation detection
     imu_.settings.accelSampleRate = 416; // High-frequency sampling
     imu_.settings.gyroSampleRate = 416;
     
     bool init_result = imu_.begin() == 0;
     heysalad::config::LogDebug(init_result ? 
       "IMU Initialization Successful" : "IMU Initialization Failed");
     
     return init_result;
   }
 
   /**
    * Initializes the microphone for audio recording.
    * 
    * @return bool True if microphone initialization was successful.
    */
   bool InitializeMicrophone() {
     heysalad::config::LogDebug("Attempting Microphone Initialization");
     
     mic_config_t mic_config{
       .channel_cnt = 1,
       .sampling_rate = heysalad::config::kAudioSampleRate,
       .buf_size = 1600,
       .debug_pin = LED_BUILTIN
     };
 
     // Create microphone instance and set callback
     MG24_ADC_Class mic(&mic_config);
     mic.set_callback(AudioRecordingCallback);
 
     bool init_result = mic.begin();
     heysalad::config::LogDebug(init_result ? 
       "Microphone Initialization Successful" : "Microphone Initialization Failed");
     
     return init_result;
   }
 
   /**
    * Updates sensor data from IMU.
    */
   void UpdateSensorData() {
     acceleration_x_ = imu_.readFloatAccelX();
     acceleration_y_ = imu_.readFloatAccelY();
     acceleration_z_ = imu_.readFloatAccelZ();
     
     // Calculate acceleration magnitude
     acceleration_magnitude_ = sqrt(
       acceleration_x_ * acceleration_x_ + 
       acceleration_y_ * acceleration_y_ + 
       acceleration_z_ * acceleration_z_
     );
   }
 
   /**
    * Detects and processes gestures based on acceleration.
    */
   void DetectGestures() {
     if (acceleration_magnitude_ >= heysalad::config::kCaptureGestureThreshold) {
       GestureType gesture_type = (acceleration_magnitude_ >= heysalad::config::kRecipeGestureThreshold)
         ? GestureType::kViewRecipe 
         : GestureType::kCaptureFood;
       
       HandleGestureDetection(gesture_type);
     }
   }
 
   /**
    * Handles specific gesture detection events.
    * 
    * @param gesture_type The type of gesture detected.
    */
   void HandleGestureDetection(GestureType gesture_type) {
     switch (gesture_type) {
       case GestureType::kCaptureFood:
         heysalad::config::LogDebug("Capture Food Gesture Detected");
         Serial1.println("GESTURE_CAPTURE");
         SendEventNotification("GESTURE_CAPTURE");
         break;
       
       case GestureType::kViewRecipe:
         heysalad::config::LogDebug("View Recipe Gesture Detected");
         Serial1.println("GESTURE_RECIPE");
         SendEventNotification("GESTURE_RECIPE");
         break;
       
       default:
         break;
     }
   }
 
   /**
    * Sends periodic sensor data.
    */
   void SendPeriodicData() {
     static unsigned long last_send_time = 0;
     
     if (millis() - last_send_time >= heysalad::config::kDataSendInterval) {
       String sensor_data = String(acceleration_x_, 3) + "," + 
                            String(acceleration_y_, 3) + "," + 
                            String(acceleration_z_, 3);
       
       Serial1.println(sensor_data);
       last_send_time = millis();
     }
   }
 
   /**
    * Processes incoming commands from serial interfaces.
    */
   void ProcessCommands() {
     ProcessSerialCommands(Serial);   // Debugging interface
     ProcessSerialCommands(Serial1);  // ESP32 communication
   }
 
   /**
    * Processes commands from a specific serial interface.
    * 
    * @param serial Reference to the serial interface to read from.
    */
   void ProcessSerialCommands(Stream& serial) {
     if (serial.available()) {
       String command = serial.readStringUntil('\n');
       command.trim();
       
       heysalad::config::LogDebug("Received Command: " + command);
       
       if (command == "heysalad start camera") {
         heysalad::config::LogDebug("Camera Start Command Detected");
         SendCommandToEsp32("START_CAMERA");
       } else if (command == "heysalad stop camera") {
         heysalad::config::LogDebug("Camera Stop Command Detected");
         SendCommandToEsp32("STOP_CAMERA");
       } else if (command == "heysalad record audio") {
         heysalad::config::LogDebug("Audio Record Command Detected");
         StartAudioRecording();
       } else {
         heysalad::config::LogDebug("Unrecognized Command");
       }
     }
   }
 
   /**
    * Sends a command to the ESP32.
    * 
    * @param command The command to send.
    */
   void SendCommandToEsp32(const String& command) {
     heysalad::config::LogDebug("Sending Command to ESP32: " + command);
     
     // Send command on both Serial interfaces for maximum chances of transmission
     Serial1.println(command);
     Serial.println("Sent to ESP32: " + command);
     
     // Optional: Add a small delay to ensure transmission
     delay(50);
     
     // Verify transmission by flushing serial buffer
     Serial1.flush();
   }
 
   /**
    * Starts audio recording process.
    */
   void StartAudioRecording() {
     is_recording_ = true;
     is_audio_ready_ = false;
     heysalad::config::LogDebug("Audio Recording Started");
   }
 
   /**
    * Sends event notification (simulated BLE notification).
    * 
    * @param event The event to notify.
    */
   void SendEventNotification(const char* event) {
     heysalad::config::LogDebug("Event Notification: " + String(event));
     Serial.println("Event: " + String(event));
   }
 
   /**
    * Static callback for audio recording.
    * 
    * @param buffer Audio data buffer.
    * @param buffer_length Length of the buffer.
    */
   static void AudioRecordingCallback(uint16_t* buffer, uint32_t buffer_length) {
     heysalad::config::LogDebug("Audio Recording Callback Triggered");
   }
 };
 
 // Global motion controller instance
 HeySaladMotionController motion_controller;
 
 /**
  * Arduino setup function.
  * Initializes the HeySalad motion controller.
  */
 void setup() {
   motion_controller.Initialize();
 }
 
 /**
  * Arduino main loop function.
  * Runs the motion controller's process loop.
  */
 void loop() {
   motion_controller.ProcessLoop();
 }