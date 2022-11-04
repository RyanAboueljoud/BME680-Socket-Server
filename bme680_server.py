"""
BME680 HTTP Web Socket Server.
Hosted on a Raspberry Pi Pico W

Displays BME680 sensor readings on
a graphical html web page.
"""

import uos
import machine
from machine import Pin, I2C
from bme680 import *
import socket
import network
import time
import math

# Check string for whole word using space as delimiter 
def contains_word(st, wd):
    return (b' ' + wd + b' ') in (b' ' + st + b' ')

# Initialize global variables
start_timestamp = time.time() # Program start time 
led = machine.Pin("LED", machine.Pin.OUT) # activity led
recv_buf="" # Socket recieve buffer
min_temp 	= 10000.0
min_humid 	= 10000.0
min_press 	= 10000.0
min_gas 	= 10000.0
min_aqi 	= 10000.0
max_temp 	= 0.0
max_humid 	= 0.0
max_press 	= 0.0
max_gas 	= 0.0
max_aqi 	= 0.0

led.on()

# Print hardware info
print()
print("Machine: \t" + uos.uname()[4])
print("MicroPython: \t" + uos.uname()[3])

# Initializing the I2C method 
i2c=I2C(0, scl=machine.Pin(17), sda=machine.Pin(16), freq=400000)
bme = BME680_I2C(i2c=i2c)

# Initialize and connect wireless lan
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("SSID","SSID_PW")
time.sleep(0.1)
sta_if = network.WLAN(network.STA_IF)
print(f'\nHost Address: {sta_if.ifconfig()[0]}') # Print local IP
print()

# Initialize listen socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.settimeout(30.0)
s.bind(addr)
s.listen(3)

led.off()

# Toggle variable for switch between html and media transfer
get_media_req = False

# Networking initialized, start listening for connections
print ('Listening for connections...')
while True:
    cl, addr = s.accept()
    cl_file = cl.makefile('rwb', 0)
    led.on()
    recv_buf = cl_file.readline()
    # Check buffer header for media or webpage request
    if not contains_word(recv_buf, b'/') and recv_buf is not None:
            try:
                if len(recv_buf) > 1:
                    request = recv_buf.split()[1].decode('ascii')
                    print(f'Retrieving {request}')
                    with open(str(request), "rb") as f:
                        response = f.read()
                    get_media_req = True
            except OSError as e:
                print(e)
                get_media_req = False
    while True:
        # print(recv_buf)    # DEBUG
        recv_buf = cl_file.readline()
        if not recv_buf or recv_buf == b'\r\n':
           break
    led.off()
    
    if not get_media_req:
        led.on()
        temperature = round(bme.temperature, 2)
        temperature_f = round(((bme.temperature * 9/5) + 32), 2)
        humid = round(bme.humidity, 2)
        press = round(bme.pressure, 2)
        gas = round(bme.gas/1000, 2)
        aqi = round((math.log(round(bme.gas/1000, 2))+0.04*round(bme.humidity, 2)), 2)
        temperature_str = str(temperature) + ' C'
        temperature_f_str = str(temperature_f) + ' F'
        humidity_str = str(humid) + ' %'
        pressure_str = str(press) + ' hPa'
        gas_str = str(gas) + ' KOhms'
        aqi_str = str(aqi)
        print (f'\nIncoming connection --> sending webpage')
        print('Temperature:', temperature_str)
        print('Humidity:', humidity_str)
        print('Pressure:', pressure_str)
        print('Gas:', gas_str)
        print('AQI:', aqi_str)
        print('-------\n')

        # min
        if temperature_f < min_temp:
            min_temp = temperature_f
        if humid < min_humid:
            min_humid = humid
        if press < min_press:
            min_press = press
        if gas < min_gas:
            min_gas = gas
        if aqi < min_aqi:
            min_aqi = aqi
        # max   
        if temperature_f > max_temp:
            max_temp = temperature_f
        if humid > max_humid:
            max_humid = humid
        if press > max_press:
            max_press = press
        if gas > max_gas:
            max_gas = gas
        if aqi > max_aqi:
            max_aqi = aqi

        response =  '<!DOCTYPE HTML>'+'\r\n'
        response += '<html><head>'+'\r\n'
        response += '<title>Plant Tent</title>'+'\r\n'
        response += '<link rel="apple-touch-icon" sizes="76x76" href="/img/apple-touch-icon.png">\r\n'
        response += '<link rel="icon" type="image/png" sizes="32x32" href="/img/favicon-32x32.png">\r\n'
        response += '<link rel="icon" type="image/png" sizes="16x16" href="/img/favicon-16x16.png">\r\n'
        response += '<link rel="manifest" href="/img/site.webmanifest">\r\n'
        response += '<link rel="mask-icon" href="/img/safari-pinned-tab.svg" color="#5bbad5">\r\n'
        response += '<link rel="shortcut icon" type="image/x-icon" href="favicon.ico">\r\n'
        response += '<meta name="msapplication-TileColor" content="#da532c">\r\n'
        response += '<meta name="msapplication-config" content="/img/browserconfig.xml">\r\n'
        response += '<meta name="theme-color" content="#ffffff">\r\n'
        response += '<meta http-equiv=\"refresh\" content=\"10\">'+'\r\n'
        response += '<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\r\n'
        response += '<style>'+'\r\n'
        response += 'html {font-family: Arial; display: inline-block; text-align: center;}'+'\r\n'
        response += 'p {  font-size: 1.2rem;}'+'\r\n'
        response += 'body {  margin: 0;}'+'\r\n'
        response += '.topnav { overflow: hidden; background-color: #5c055c; color: white; font-size: 1.7rem; }'+'\r\n'
        response += '.content { padding: 20px; }'+'\r\n'
        response += '.card { background-color: white; box-shadow: 2px 2px 12px 1px rgba(140,140,140,.5); }'+'\r\n'
        response += '.cards { max-width: 700px; margin: 0 auto; display: grid; grid-gap: 2rem; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }'+'\r\n'
        response += '.reading { font-size: 2.8rem; }'+'\r\n'
        response += '.card.temperature { color: #0e7c7b; }'+'\r\n'
        response += '.card.humidity { color: #17bebb; }'+'\r\n'
        response += '.card.pressure { color: hsl(113, 61%, 29%); }'+'\r\n'
        response += '.card.gas { color: #5c055c; }'+'\r\n'
        response += '</style>'+'\r\n'
        response += '</head>'+'\r\n'
        response += '<body>'+'\r\n'
        response += '<div class=\"topnav\">'+'\r\n'
        response += '<h3><img src=/img/favicon-32x32.png alt="Potted Plant Left"> Exotic Plant Tent Stats <img src=/img/favicon-32x32.png alt="Potted Plant Right"></h3>'+'\r\n'
        response += '</div>'+'\r\n'
        response += '<div class=\"content\">'+'\r\n'
        response += '<div class=\"cards\">'+'\r\n'
        response += '<div class=\"card temperature\">'+'\r\n'
        response += '<h4>Temp. Celsius</h4><p><span class=\"reading\">' + temperature_f_str + '<br><h4>' + temperature_str + f'<br>min: {min_temp} C max: {max_temp} C</h4></p>'+'\r\n'
        response += '</div>'+'\r\n'
        response += '<div class=\"card humidity\">'+'\r\n'
        response += '<h4>Humidity</h4><p><span class=\"reading\">' + humidity_str + f'<br><h4>min: {min_humid} max: {max_humid}</h4></p>'+'\r\n'
        response += '</div>'+'\r\n'
        response += '<div class=\"card pressure\">'+'\r\n'
        response += '<h4>PRESSURE</h4><p><span class=\"reading\">' + pressure_str + f'<br><h4>min: {min_press} max: {max_press}</h4></p>'+'\r\n'
        response += '</div>'+'\r\n'
        response += '<div class=\"card gas\">' +'\r\n'
        response += '<h4>Gas</h4><p><span class=\"reading\">' + 'AQI: ' + aqi_str + f'<h4>min: {min_aqi} max: {max_aqi}</h4><h2>'+ gas_str + f'</h2><h4>min: {min_gas} max: {max_gas}</h4></p>'+'\r\n'
        seconds = (time.time() - start_timestamp) % (24 * 3600)
        hours = round((seconds / 3600), 4)
        response += f'</div></div><br>Runtime: {hours} hour(s)</div>'+'\r\n'
        response += '</body></html>'+'\r\n'
        led.off()

    try:
        led.on()
        if not get_media_req:    # Toggle response type between html and favicon
            cl.send('HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n')
            cl.send(response)
        else:
            print(f'Sending {request}')
            if contains_word(request, '/img/site.webmanifest'):
                content_type = 'application/manifest+json'
            elif contains_word(request, 'favicon.png'):
                content_type = 'image/x-icon'
            else:
                content_type = 'image/png'
            cl.send(f'HTTP/1.0 200 OK\r\nContent-type: {content_type}\r\nAccept-Ranges: bytes\r\nCache-Control: max-age=604800\r\n\r\n')
            cl.send(response)
            
        get_media_req = False
        cl.close()
    except OSError as e:
        print(e)
        cl.close()
    
    led.off()
    recv_buf="" # Reset buffer
    response="" # Reset response
    print ('Listening for connections...\n')
