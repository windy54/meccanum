/*********
  Rui Santos & Sara Santos - Random Nerd Tutorials
  Complete instructions at https://RandomNerdTutorials.com/esp32-cam-projects-ebook/
  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files.
  The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.


board type :AI Thinker ESP32-cam Minimal spiffs with ota
*********/

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_timer.h"
#include "img_converters.h"
#include "Arduino.h"
#include "fb_gfx.h"
#include "soc/soc.h"             // disable brownout problems
#include "soc/rtc_cntl_reg.h"    // disable brownout problems
#include "esp_http_server.h"

#include "esp_ota_ops.h"
#include "esp_partition.h"

#include "web.h"



extern String mecmode;
void initPicoCmds();

// Define the RX and TX pins for Serial 2
#define RXD2 12
#define TXD2 13

#define PICO_BAUD 19200

unsigned long previousMillis = 0;
bool ledState = 0;
bool ledFlashState = true;
const int ledPin = 33;
const int ledFlash =4;

// Create an instance of the HardwareSerial class for Serial 2
HardwareSerial picoSerial(2);

String mecmode = "{\"status\":\"u\",\"autostatus\":\"u\",\"range\":0,\"volts\":0}";


void toggleLED(){
  ledState = !ledState;
    digitalWrite(ledPin, ledState);
}





#define CAMERA_MODEL_AI_THINKER


  #define PWDN_GPIO_NUM     32
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM      0
  #define SIOD_GPIO_NUM     26
  #define SIOC_GPIO_NUM     27
  
  #define Y9_GPIO_NUM       35
  #define Y8_GPIO_NUM       34
  #define Y7_GPIO_NUM       39
  #define Y6_GPIO_NUM       36
  #define Y5_GPIO_NUM       21
  #define Y4_GPIO_NUM       19
  #define Y3_GPIO_NUM       18
  #define Y2_GPIO_NUM        5
  #define VSYNC_GPIO_NUM    25
  #define HREF_GPIO_NUM     23
  #define PCLK_GPIO_NUM     22



bool camera_ok = false;

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); //disable brownout detector
  
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
  
  pinMode(ledFlash, OUTPUT);
  digitalWrite(ledFlash, LOW);
  
  Serial.begin(115200);
  Serial.setDebugOutput(false);
  
  picoSerial.begin(PICO_BAUD,SERIAL_8N1, RXD2, TXD2);
  
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_GRAYSCALE; //PIXFORMAT_JPEG; 
  config.frame_size   = FRAMESIZE_QVGA;      // 320x240 if this i changed edit linedetect out array
  config.grab_mode    = CAMERA_GRAB_LATEST;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 15;                  // JPEG quality used later
  config.fb_count     = 1;
  
  
  // Camera init
  
   for (int i = 0; i < 3 && !camera_ok; i++) {
    esp_err_t err = esp_camera_init(&config);
    if (err == ESP_OK) {
      camera_ok = true;
    } else {
      Serial.printf("Camera init failed with error 0x%x, retry %d\n", err, i);
      delay(200);   // short pause, let rails settle
      // optional: do a camera/I2C reset here (see below)
    }
  }

  if (!camera_ok) {
    Serial.println("Camera failed after retries, restarting...");
    ESP.restart();    // last resort: full reset
  }
  // now flip image
  sensor_t * s = esp_camera_sensor_get();
  s->set_vflip(s, 1);   // 1 = enable vertical flip, 0 = disable
  // s->set_hmirror(s, 1); // optional horizontal mirror

  /*
   * // Wi-Fi connection
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  */
  WiFi.softAP("meccanum", "meccanum");

  IPAddress IP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(IP);
  Serial.print("Camera Stream Ready! Go to: http://");
  Serial.println(WiFi.localIP());
  
  // Start streaming web server
  startCameraServer();
  initPicoCmds();
}

void loop() {

// Check if data is available to read every 100 milli secs
  unsigned long currentMillis=millis();
  if (currentMillis - previousMillis >= 100) // check for data at 10Hz
  {
    
    previousMillis = currentMillis;
    //sendPicoCmd("forwards",0);
    if (picoSerial.available()) {
      // Read data and display it
      String message = picoSerial.readStringUntil('\n');
      //Serial.println("Received: " + message);
      ledFlashState=!ledFlashState;
      digitalWrite(ledFlash, ledFlashState);
      // need to decode message
      if (message !="")mecmode = message;
      //picoSerial.println("got you");
      
      
    }
  }
  
}
