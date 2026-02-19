// Central band: from ystart to yend (you already use 3h/8..5h/8 → 120 rows)
// Use exact numbers for clarity: 320 width, 120 rows.



static uint8_t bandBuf[320 * 120];  // 38,400 bytes in internal RAM


#define CAMERA_MODEL_AI_THINKER


void startCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = 5;   //Y2_GPIO_NUM;
  config.pin_d1       = 18; //Y3_GPIO_NUM;
  config.pin_d2       = 19; //Y4_GPIO_NUM;
  config.pin_d3       = 21; //Y5_GPIO_NUM;
  config.pin_d4       = 36; //Y6_GPIO_NUM;
  config.pin_d5       = 39; //Y7_GPIO_NUM;
  config.pin_d6       = 34; //Y8_GPIO_NUM;
  config.pin_d7       = 35; //Y9_GPIO_NUM;
  config.pin_xclk     = 0; //CLK_GPIO_NUM;
  config.pin_pclk     = 22; //PCLK_GPIO_NUM;
  config.pin_vsync    = 25; //VSYNC_GPIO_NUM;
  config.pin_href     = 23; //HREF_GPIO_NUM;
  config.pin_sscb_sda = 26; //SIOD_GPIO_NUM;
  config.pin_sscb_scl = 27; //SIOC_GPIO_NUM;
  config.pin_pwdn     = 32; //PWDN_GPIO_NUM;
  config.pin_reset    = -1; //RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;

  config.frame_size   = FRAMESIZE_QVGA;      // 320x240 if this i changed edit linedetect out array
  config.pixel_format = PIXFORMAT_GRAYSCALE; // 1 byte per pixel[web:16][web:17]
  config.grab_mode    = CAMERA_GRAB_LATEST;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 15;                  // JPEG quality used later
  config.fb_count     = 1;
  bool cameraNotDetected = true;
  while(cameraNotDetected){
    esp_err_t err = esp_camera_init(&config);
    if (err == ESP_OK) {
      cameraNotDetected = false;
      
    }
    Serial.printf("Camera init failed 0x%x\n", err);
    delay(50);
  }
}

void processGrayscale(camera_fb_t *fb) {
  uint8_t* img = fb->buf;
  int w = fb->width;
  int h = fb->height;

  // Find global min/max
  uint8_t gmin = 255, gmax = 0;
  for (int i = 0; i < w * h; i++) {
    uint8_t p = img[i];
    if (p < gmin) gmin = p;
    if (p > gmax) gmax = p;
  }
  if (gmax == gmin) return;

  int diff = gmax - gmin;

  for (int i = 0; i < w * h; i++) {
    int stretched = (img[i] - gmin) * 255 / diff;
    img[i] = stretched > 128 ? 255 : 0;  // simple binary image
  }
}

int detectLineEdges(camera_fb_t *fb) {
  uint8_t *img = fb->buf;
  const int w = fb->width;
  const int h = fb->height;
  const int ystart = (3 * h) / 8;
  const int yend   = (5 * h) / 8;
const int bandHeight = yend - ystart; // 60 rows with your current math; adjust as needed

  // Adjust bandBuf size accordingly if you change bandHeight.
  // Copy the band into fast buffer
  for (int y = 0; y < bandHeight; y++) {
    memcpy(&bandBuf[y * w], &img[(ystart + y) * w], w);
  }
    int averageCount = 0;
  int averagePosition = 0;

  for (int y = 0; y < bandHeight; y++) {
    uint8_t *row = &bandBuf[y * w];

    int darkest = 255;
    int brightest = 0;
    int edges[2];
    int edgeIndex = 0;

    // find min / max in this row
    for (int x = 0; x < w; x++) {
      uint8_t v = row[x];
      if (v < darkest) darkest = v;
      if (v > brightest) brightest = v;
    }

    int diff = brightest - darkest;
    if (diff == 0) {
      continue;  // flat row, skip
    }

    const int scale = (255 << 8) / diff;
    uint8_t prevPixel = 0;

    for (int x = 0; x < w; x++) {
      int v = row[x] - darkest;
      if (v < 0) v = 0;

      int pixel = (v * scale) >> 8;
      pixel = (pixel > 128) ? 255 : 0;

      row[x] = (uint8_t)pixel;

      if (x > 0) {
        int d = pixel - prevPixel;
        if (d < 0) d = -d;
        uint8_t edgeVal = (d == 255) ? 255 : 0;

        if (edgeVal == 255 && edgeIndex < 2) {
          edges[edgeIndex++] = x;
          if (edgeIndex == 2) {
            int pos = (edges[0] + edges[1]) / 2;
            int width = edges[1] - edges[0];
            if (width > 50) {
              averagePosition += pos;
              averageCount++;
            }
            edgeIndex = 0;
          }
        }
      }
      prevPixel = pixel;
    }
  }
  // After processing bandBuf
  for (int y = 0; y < bandHeight; y++) {
    memcpy(&img[(ystart + y) * w], &bandBuf[y * w], w);
  }

  if (averageCount > 0) averagePosition /= averageCount;
  return averagePosition;
}
