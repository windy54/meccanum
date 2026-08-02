import socket
import ujson
import random
from _thread import allocate_lock

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen()
s.settimeout(0.1)  # 100ms max wait for a new web connection

print('Listening on', addr)

# Initialize variables
volts = "5.1"
status = "a"
distance = 0
last_message = ""

# Shared data
shared_lock = allocate_lock()

def update_from_serial(line):
    global shared_lock, last_message
    #print("update from serial", line)
    with shared_lock:
        last_message = line
    #print(last_message)

def get_status():
    global shared_lock, last_message
    with shared_lock:
        data = last_message
    #print(data)
    return data


def webpage(distance, state, volts):
    html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pico Web Server</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
            <h1>Raspberry Pi Pico Web Server</h1>
            <h2>Normal</h2>
            <table>
            <tr><td></td><td><form action="./forward">
                <input type="submit" value="Forward" />
            </form>
            </td><td></td></tr>
             <tr><td><form action="./left">
                <input type="submit" value="Left" /></td>
            <td></form>
             <form action="./stop">
                <input type="submit" value="Stop" /></td>
            <td></form>
             <form action="./right">
                <input type="submit" value="Right" />
            </form></td></tr>
            <tr><td></td><td>
            <form action="./backward">
                <input type="submit" value="Backward" />
            </form></td><td></td></tr>
            </table>
             <h2>Advanced</h2>
            <table><tr><td><form action="./sl">
                <input type="submit" value="Strafe Left" /></td>
            <td></form>
             <form action="./auto">
                <input type="submit" value="Automatic" /></td>
            <td></form>
             <form action="./sr">
                <input type="submit" value="Strafe Right" />
            </form></td></tr></table>
            <h2>Status</h2>
            <p>status: <span id="state">{state}</span></p>
            <p>Voltage:<span id="volts">{volts} </span></p>
            <p>Distance:<span id="distance">{distance} </span></p>
           <script>
            async function updateData() {{
                try {{
                    const r = await fetch('/data?');
                    const d = await r.json();
                    console.log(d);
                    document.getElementById('state').textContent = d.status;
                    document.getElementById('volts').textContent = d.volts;
                    document.getElementById('distance').textContent = d.range;
                }} catch (e) {{
                    console.log(e);
                }}
            }}

            updateData();
            setInterval(updateData, 500);
        </script>
        </body>
        </html>
        """
    return str(html)

def data_handler():
    
    return get_status() #ujson.dumps(data)


def getWebCMD():
    global state, random_value, status, volts, distance
    rxCMD = ""
    try:
        conn, addr = s.accept()
        conn.settimeout(1)  # accepted connection gets a longer timeout
    except OSError:
        # No web client connected within the 100ms window
        return rxCMD

    try:
        request = conn.recv(1024)
        request = str(request)

        try:
            request = request.split()[1]
        except IndexError:
            pass

        # Process the request and update variables
        if request == '/forward?':
            rxCMD = "forwards"
        elif request == '/backward?':
            rxCMD = "back"
        elif request == '/right?':
            rxCMD = "right"
        elif request == '/left?':
            rxCMD = "left"
        elif request == '/stop?':
            rxCMD = "stop"
        elif request == '/sl?':
            rxCMD = "sl"
        elif request == '/auto?':
            rxCMD = "auto"
        elif request == '/sr?':
            rxCMD = "sr"
        elif request == '/data?':
            #print("data request")
            response = data_handler()

            conn.send('HTTP/1.0 200 OK\r\n')
            conn.send('Content-Type: application/json\r\n')
            conn.send('Connection: close\r\n\r\n')
            conn.send(response)
            conn.close()
            return rxCMD

        # Generate HTML response
        response = webpage(distance, status, volts)

        # Send the HTTP response and close the connection
        conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        conn.send(response)
        conn.close()
    except OSError as e:
        conn.close()
        print('Connection closed:', e)
    return rxCMD