# meccanum
ESP32-cam code and motor2040 code for a meccanum robot
The ESP32-cam code creates a webpage to display video, give the operator controls to controlthe robot,
select an automatic mode where the robot moves forward and when it gets withon 10cm of an obstruction moves to the right until a gap is found.
Commands from the web are sent to a motor2040 card to control the motors using micropython (pimoroni version).
Status from the moto2040 is then sent to the ESP32 and displayed on the webpage.

This code will be edited to add a line following mode.
