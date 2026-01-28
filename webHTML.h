
static const char PROGMEM UPDATE_HTML[] = R"rawliteral(
<html>
  <head>
    <title>Meccanum OTA Update</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
  </head>
  <body>
    <h1>Meccanum OTA Update</h1>

    <input type="file" id="firmware" accept=".bin"><br><br>
    <button onclick="uploadFirmware()">Upload & Update</button>

    <p id="status"></p>
    <p><a href="/">Back to robot</a></p>

    <script>
      async function uploadFirmware() {
        const fileInput = document.getElementById('firmware');
        const status = document.getElementById('status');

        if (!fileInput.files.length) {
          status.textContent = 'Please choose a .bin file first.';
          return;
        }

        const file = fileInput.files[0];

        try {
          status.textContent = 'Uploading...';

          const res = await fetch('/update', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/octet-stream'
            },
            body: file
          });

          const text = await res.text();
          status.textContent = 'Response: ' + text;
        } catch (e) {
          status.textContent = 'Upload failed: ' + e;
        }
      }
    </script>
  </body>
</html>

)rawliteral";



static const char PROGMEM INDEX_HTML[] = R"rawliteral(
<html>
  <head>
    <title>ESP32-CAM Robot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: Arial; text-align: center; margin:0px auto; padding-top: 30px;}
      table { margin-left: auto; margin-right: auto; }
      td { padding: 8 px; }
      .button {
        background-color: #2f4468;
        border: none;
        color: white;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 18px;
        margin: 6px 3px;
        cursor: pointer;
        -webkit-touch-callout: none;
        -webkit-user-select: none;
        -khtml-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
        -webkit-tap-highlight-color: rgba(0,0,0,0);
      }
      img {  width: auto ;
        max-width: 100% ;
        height: auto ; 
      }
    </style>
  </head>
  <body>
    <h1>ESP32-CAM Robot</h1>
    <img src="" id="photo" >
    <table>
      <tr><td colspan="3" align="center"><button class="button" onmousedown="toggleCheckbox('forward');" ontouchstart="toggleCheckbox('forward');">Forward</button></td></tr>
      <tr><td align="center"><button class="button" onmousedown="toggleCheckbox('left');" ontouchstart="toggleCheckbox('left');" >Left</button></td><td align="center"><button class="button" onmousedown="toggleCheckbox('stop');" ontouchstart="toggleCheckbox('stop');">Stop</button></td><td align="center"><button class="button" onmousedown="toggleCheckbox('right');" ontouchstart="toggleCheckbox('right');" >Right</button></td></tr>
      <tr><td colspan="3" align="center"><button class="button" onmousedown="toggleCheckbox('backward');" ontouchstart="toggleCheckbox('backward');" >Backward</button></td></tr>
      <tr><td colspan="3" align="center"><button class="button" onmousedown="toggleCheckbox('auto');" ontouchstart="toggleCheckbox('auto');" >Automatic</button></td></tr>                   
    </table>
    <p>Status: <span id="status">-</span></p>
    <p>Auto: <span id="autostatus">-</span></p>
    <p>Range: <span id="range">-</span></p>
    <p>Volts: <span id="volts">-</span></p>
    
    
   <script>
   function toggleCheckbox(x) {
     var xhr = new XMLHttpRequest();
     xhr.open("GET", "/action?go=" + x, true);
     xhr.send();
   }
   window.onload = document.getElementById("photo").src = window.location.href.slice(0, -1) + ":81/stream";
  
if (!!window.EventSource) {
  var source = new EventSource('/events');

  source.addEventListener('message', function(e) {
    // e.data is a JSON string, same as mecmode
    try {
      const data = JSON.parse(e.data);
      document.getElementById('status').textContent = data.status;
      document.getElementById('autostatus').textContent = data.autostatus;
      document.getElementById('range').textContent = data.range;
      document.getElementById('volts').textContent = data.volts;
    } catch (err) {
      console.error('Bad SSE JSON', err);
    }
  }, false);

  source.addEventListener('open', function(e) {
    console.log("Events Connected");
  }, false);

  source.addEventListener('error', function(e) {
    if (e.target.readyState != EventSource.OPEN) {
      console.log("Events Disconnected");
    }
  }, false);
} else {
  console.error("SSE not supported in this browser");
}
</script>
  </body>
  
</html>
)rawliteral";
