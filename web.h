
#include "webHTML.h"

extern String mecmode;
extern String lastMecmodeSent;
extern void toggleLED();
extern HardwareSerial picoSerial;
#define PART_BOUNDARY "123456789000000000000987654321"


static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t camera_httpd = NULL;
httpd_handle_t stream_httpd = NULL;

/*
 * 
 */

 /*
 * code for OTA
 */
typedef struct {
  esp_ota_handle_t handle;
  const esp_partition_t *update_partition;
  size_t received;
  bool started;
} ota_upload_ctx_t;
static ota_upload_ctx_t ota_ctx;

static esp_err_t ota_post_handler(httpd_req_t *req) {
  esp_err_t err;
  int remaining = req->content_len;

  if (!ota_ctx.started) {
    ota_ctx.update_partition = esp_ota_get_next_update_partition(NULL);
    if (ota_ctx.update_partition == NULL) {
      httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "No OTA partition");
      return ESP_FAIL;
    }
    err = esp_ota_begin(ota_ctx.update_partition, OTA_SIZE_UNKNOWN, &ota_ctx.handle);
    if (err != ESP_OK) {
      httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "esp_ota_begin failed");
      return ESP_FAIL;
    }
    ota_ctx.started = true;
    ota_ctx.received = 0;
  }

  char buf[1024];
  while (remaining > 0) {
    int to_read = remaining > sizeof(buf) ? sizeof(buf) : remaining;
    int read_len = httpd_req_recv(req, buf, to_read);
    if (read_len <= 0) {
      if (read_len == HTTPD_SOCK_ERR_TIMEOUT) {
        continue; // retry
      }
      httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Receive error");
      return ESP_FAIL;
    }

    err = esp_ota_write(ota_ctx.handle, buf, read_len);
    if (err != ESP_OK) {
      httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "esp_ota_write failed");
      return ESP_FAIL;
    }

    ota_ctx.received += read_len;
    remaining -= read_len;
  }

  err = esp_ota_end(ota_ctx.handle);
  if (err != ESP_OK) {
    httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "esp_ota_end failed");
    return ESP_FAIL;
  }

  err = esp_ota_set_boot_partition(ota_ctx.update_partition);
  if (err != ESP_OK) {
    httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "set_boot_partition failed");
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "text/plain");
  httpd_resp_sendstr(req, "OK, rebooting");

  // Give the response time to go out
  delay(100);
  esp_restart();
  return ESP_OK; // not reached
}
/*
 * 
 */
 //
 static esp_err_t events_handler(httpd_req_t *req) {
  // Standard SSE headers
  httpd_resp_set_type(req, "text/event-stream");
  httpd_resp_set_hdr(req, "Cache-Control", "no-cache");
  httpd_resp_set_hdr(req, "Connection", "keep-alive");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  // Initial send of current state
  String payload = "data: " + mecmode + "\n\n";
  httpd_resp_send_chunk(req, payload.c_str(), payload.length());

  // Now keep the connection open and push when mecmode changes
  while (true) {
    if (mecmode != lastMecmodeSent) {
      lastMecmodeSent = mecmode;
      String msg = "data: " + mecmode + "\n\n";
      if (httpd_resp_send_chunk(req, msg.c_str(), msg.length()) != ESP_OK) {
        break; // client disconnected
      }
    }
    vTaskDelay(pdMS_TO_TICKS(500)); // small sleep to avoid busy loop
  }

  httpd_resp_send_chunk(req, NULL, 0); // terminate
  return ESP_OK;
}

static esp_err_t index_handler(httpd_req_t *req){
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, (const char *)INDEX_HTML, strlen(INDEX_HTML));
}

static esp_err_t update_page_handler(httpd_req_t *req){
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, (const char *)UPDATE_HTML, strlen(UPDATE_HTML));
}


static esp_err_t stream_handler(httpd_req_t *req){
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char * part_buf[64];

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if(res != ESP_OK){
    return res;
  }

  while(true){
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
    } else {
      if(fb->width > 400){
        if(fb->format != PIXFORMAT_JPEG){
          bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
          esp_camera_fb_return(fb);
          fb = NULL;
          if(!jpeg_converted){
            Serial.println("JPEG compression failed");
            res = ESP_FAIL;
          }
        } else {
          _jpg_buf_len = fb->len;
          _jpg_buf = fb->buf;
        }
      }
    }
    if(res == ESP_OK){
      size_t hlen = snprintf((char *)part_buf, 64, _STREAM_PART, _jpg_buf_len);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    }
    if(fb){
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if(_jpg_buf){
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if(res != ESP_OK){
      break;
    }
    //Serial.printf("MJPG: %uB\n",(uint32_t)(_jpg_buf_len));
  }
  return res;
}

static esp_err_t cmd_handler(httpd_req_t *req){
  char*  buf;
  size_t buf_len;
  char variable[32] = {0,};
  Serial.println("cmd handler start");
  buf_len = httpd_req_get_url_query_len(req) + 1;
  Serial.print("query len="); Serial.println(buf_len);
  if (buf_len > 1) {
    buf = (char*)malloc(buf_len);
    if(!buf){
      httpd_resp_send_500(req);
      return ESP_FAIL;
    }
    if (httpd_req_get_url_query_str(req, buf, buf_len) == ESP_OK) {
      
      if (httpd_query_key_value(buf, "go", variable, sizeof(variable)) == ESP_OK) {
        Serial.print("go="); Serial.println(variable);
      } else {
        free(buf);
        httpd_resp_send_404(req);
        return ESP_FAIL;
      }
    } else {
      free(buf);
      httpd_resp_send_404(req);
      return ESP_FAIL;
    }
    free(buf);
  } else {
    httpd_resp_send_404(req);
    return ESP_FAIL;
  }

  sensor_t * s = esp_camera_sensor_get();
  int res = 0;
  
  if(!strcmp(variable, "forward")) {
    Serial.println("Forward");
    toggleLED();
    picoSerial.println("f\n");
  }
  else if(!strcmp(variable, "left")) {
    Serial.println("Left");
    toggleLED();
    picoSerial.println("l\n");
  }
  else if(!strcmp(variable, "right")) {
    Serial.println("Right");
    toggleLED();
    picoSerial.println("r\n");
  }
  else if(!strcmp(variable, "backward")) {
    Serial.println("Backward");
    toggleLED();
    picoSerial.println("b\n");
  }
  else if(!strcmp(variable, "stop")) {
    Serial.println("Stop");
    toggleLED();
    picoSerial.println("s\n");
  }
  else if(!strcmp(variable, "auto")) {
    Serial.println("Auto");
    toggleLED();
    picoSerial.println("a\n");
  }
  else {
    res = -1;
  }

  if(res){
    return httpd_resp_send_500(req);
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, NULL, 0);
}


static esp_err_t status_get_handler(httpd_req_t *req)
{
    const char *resp_str =mecmode.c_str();

    // Tell browser this is JSON
    httpd_resp_set_type(req, "application/json");

    // Optionally set status code, default is 200
    // httpd_resp_set_status(req, "200 OK");

    // Send body
    httpd_resp_send(req, resp_str, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

void startCameraServer(){
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  httpd_uri_t index_uri = {
    .uri       = "/",
    .method    = HTTP_GET,
    .handler   = index_handler,
    .user_ctx  = NULL
  };
httpd_uri_t events_uri = {
  .uri       = "/events",
  .method    = HTTP_GET,
  .handler   = events_handler,
  .user_ctx  = NULL
};
  httpd_uri_t cmd_uri = {
    .uri       = "/action",
    .method    = HTTP_GET,
    .handler   = cmd_handler,
    .user_ctx  = NULL
  };
  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

   httpd_uri_t status_uri = {
            .uri      = "/status",
            .method   = HTTP_GET,
            .handler  = status_get_handler,
            .user_ctx = NULL
   };

   //
   httpd_uri_t update_page_uri = {
    .uri       = "/update",
    .method    = HTTP_GET,
    .handler   = update_page_handler,
    .user_ctx  = NULL
  };
  
   httpd_uri_t ota_uri = {
    .uri       = "/update",
    .method    = HTTP_POST,
    .handler   = ota_post_handler,
    .user_ctx  = NULL
  };
  //
  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &cmd_uri);
    httpd_register_uri_handler(camera_httpd, &status_uri);
    httpd_register_uri_handler(camera_httpd, &update_page_uri);
    httpd_register_uri_handler(camera_httpd, &ota_uri);
    httpd_register_uri_handler(camera_httpd, &events_uri); 
  }
  config.server_port += 1;
  config.ctrl_port += 1;
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }

  
}
