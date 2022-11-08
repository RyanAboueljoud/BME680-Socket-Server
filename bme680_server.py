"""
BME680 HTTP Web Socket Server.
Hosted on a Raspberry Pi Pico W

Displays BME680 sensor readings on
a graphical html web page.
"""

import uos
from machine import Pin, I2C

import wlan_setup
from bme680 import *
import socket
import time
import math

import ntp_client as ntp


# Check string for whole word using space as delimiter 
def contains_word(st, wd):
    return (b' ' + wd + b' ') in (b' ' + st + b' ')


# Initialize global variables
days = 0    # Counter for days of runtime, Pico W resets system time every 24H
led = Pin("LED", Pin.OUT)   # activity led
recv_buf = ""   # Socket receive buffer
fieldnames = ['date', 'time', 'Temp_C', 'Temp_F', 'Humidity', 'Pressure', 'Gas', 'AQI']     # CSV
min_temp    = 10000.0
min_humid   = 10000.0
min_press   = 10000.0
min_gas     = 10000.0
min_aqi     = 10000.0
max_temp    = 0.0
max_humid   = 0.0
max_press   = 0.0
max_gas     = 0.0
max_aqi     = 0.0

led.on()

# Print hardware info
print()
print("Machine: \t" + uos.uname()[4])
print("MicroPython: \t" + uos.uname()[3])

# Initializing the I2C method 
i2c=I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
bme = BME680_I2C(i2c=i2c)

# Initialize and connect wireless lan
wlan_setup.connect()

# Sync NTP Online
ntp.setup()
start_timestamp = time.mktime(time.localtime())     # Program start time
csv_sample = start_timestamp

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

download_token = time.mktime(time.localtime())
request = ''
response = ''
recv_buf = ''

# Networking initialized, start listening for connections
print('Listening for connections...')
while True:
    # Listen for new connection request
    try:
        # print(wlan.status(), network.STAT_IDLE)  # DEBUG
        cl, addr = s.accept()
        led.on()
        cl_file = cl.makefile('rwb', 0)
        recv_buf = cl_file.readline()
    except OSError as e:
        print(f'Error Receiving Request: {e}')
        recv_buf = ""
        led.off()
        try:
            cl.close()
        except NameError as e:
            print(e)
        time.sleep_ms(10)
        continue
    
    # Check buffer header for media or webpage request
    if not contains_word(recv_buf, b'/') and len(recv_buf) > 1:
        try:
            request = recv_buf.split()[1].decode('ascii')
            print(f'{request} Requested')
            get_media_req = True
            with open(str(request), "rb") as f:
                response = f.read()
        except OSError as e:
            print(f'Error Parsing Request: {e}')
    while True:
        # print(recv_buf)    # DEBUG
        if not recv_buf or recv_buf == b'\r\n' or len(recv_buf) == 0:
           break
        else:
            recv_buf = cl_file.readline()       
    led.off()

    # Get current time and date
    year, month, mday, hour, minute, second, weekday, yearday = time.localtime()
    for x in range(8):   # Convert UTC time to Pacific Timezone (UTC-08:00)
        if hour < 1:
            hour = 12
        hour -= 1
    date = f'{mday}-{month}-{year}'
    time_now = f'{hour}:{minute}:{second}'
    now = time.mktime(time.localtime())

    if not get_media_req:
        for x in range(3):  # Warm up sensor before reporting readings
            temperature = round(bme.temperature, 2)
            temperature_f = round(((bme.temperature * 9/5) + 32), 2)
            humid = round(bme.humidity, 2)
            press = round(bme.pressure, 2)
            gas = round(bme.gas/1000, 2)
            aqi = round((math.log(round(bme.gas/1000, 2))+0.04*round(bme.humidity, 2)), 2)
            time.sleep_us(10)
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

        if (now - csv_sample) > 3600:   # Record sensor readings at least every hour
            print("Writing sensor values to csv...")
            rows = [
                date,
                time_now,
                temperature,
                temperature_f,
                humid,
                press,
                gas,
                aqi
            ]

            # Check for existing stats.csv file, create a new one if not found
            try:
                f = open('stats.csv', 'r')
            except OSError as e:
                print(f'CSV may not exist: {e}')
                print('Creating new csv...')
                try:
                    with open('stats.csv', 'w') as f:
                        for x in fieldnames:
                            f.write(x)
                            if x == fieldnames[-1]:
                                f.write('\r\n')
                            else:
                                f.write(',')
                except TypeError as e:
                    print(f'TypeError writing headers to csv: {e}')
                except NameError as e:
                    print(e)
            finally:
                try:
                    f.close()
                except OSError as e:
                    print(f'CSV may not exist: {e}')

            # Append sensor readings to csv
            try:
                with open('stats.csv', 'a') as f:
                    for x in rows:
                        f.write(str(x))
                        if x == rows[-1]:
                            f.write('\r\n')
                        else:
                            f.write(',')
                csv_sample = time.mktime(time.localtime())
                print("Done.")
            except TypeError as e:
                print(f'TypeError appending to csv: {e}')
            except NameError as e:
                print(f'NameError appending to csv: {e}')

        # Set min/max
        if temperature_f < min_temp:    # min
            min_temp = temperature_f
        if humid < min_humid:
            min_humid = humid
        if press < min_press:
            min_press = press
        if gas < min_gas:
            min_gas = gas
        if aqi < min_aqi:
            min_aqi = aqi
        if temperature_f > max_temp:    # max
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
        response += f'<meta http-equiv=\"refresh\" content=\"15; url=\'http://{wlan_setup.getIp()}\'\">'+'\r\n'
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
        response += '.downloadButton{box-shadow:0 10px 14px -7px #3dc21b;background:linear-gradient(to bottom,#44c767 5%,#5cbf2a 100%);background-color:#44c767;border-radius:8px;display:inline-block;cursor:pointer;color:#fff;font-family:Arial;font-size:16px;font-weight:700;padding:13px 16px;text-decoration:none;text-shadow:0 1px 0 #2f6627}\r\n'
        response += '.downloadButton:hover{background:linear-gradient(to bottom,#5cbf2a 5%,#44c767 100%);background-color:#5cbf2a}\r\n'
        response += '.deleteButton:active,.downloadButton:active{position:relative;top:1px}.deleteButton{box-shadow:0 10px 14px -7px #cf866c;background:linear-gradient(to bottom,#d0451b 5%,#bc3315 100%);background-color:#d0451b;border-radius:8px;display:inline-block;cursor:pointer;color:#fff;font-family:Arial;font-size:12px;font-weight:700;padding:8px 10px;text-decoration:none;text-shadow:0 1px 0 #854629}.deleteButton:hover{background:linear-gradient(to bottom,#bc3315 5%,#d0451b 100%);background-color:#bc3315}\r\n'
        response += '.downloadButton:active{position:relative;top:1px}\r\n'
        response += '</style>'+'\r\n'
        response += '</head>'+'\r\n'
        response += '<body>'+'\r\n'
        response += '<div class=\"topnav\">'+'\r\n'
        response += '<h3><img src=/img/favicon-32x32.png alt="Potted Plant Left"> Exotic Plant Tent <img src=/img/favicon-32x32.png alt="Potted Plant Right"></h3>'+'\r\n'
        response += '</div>'+'\r\n'
        response += '<div class=\"content\">'+'\r\n'
        response += '<div class=\"cards\">'+'\r\n'
        response += '<div class=\"card temperature\">'+'\r\n'
        response += '<h4>Temp. Fahrenheit</h4><p><span class=\"reading\">' + temperature_f_str + '<br><h4>' + temperature_str + f'<br>min: {min_temp} F max: {max_temp} F</h4></p>'+'\r\n'
        response += '</div>'+'\r\n'
        response += '<div class=\"card humidity\">'+'\r\n'
        response += '<h4>Humidity</h4><p><span class=\"reading\">' + humidity_str + f'<br><h4>min: {min_humid} max: {max_humid}</h4></p>'+'\r\n'
        response += '</div>'+'\r\n'
        response += '<div class=\"card gas\">' + '\r\n'
        response += '<h4>Gas</h4><p><span class=\"reading\">' + 'AQI: ' + aqi_str + f'<h4>min: {min_aqi} max: {max_aqi}</h4><h2>' + gas_str + f'</h2><h4>min: {min_gas} max: {max_gas}</h4></p>' + '\r\n'
        response += '</div>'+'\r\n'
        response += '<div class=\"card pressure\">' + '\r\n'
        response += '<h4>PRESSURE</h4><p><span class=\"reading\">' + pressure_str + f'<br><h4>min: {min_press} max: {max_press}</h4></p>' + '\r\n'
        seconds = (time.time() - start_timestamp) % (24 * 3600)     # Pico W will refresh count every 24 hours
        hours = round((seconds / 3600), 4)
        if hours > 23.0000:     # NEED TO FIX - Multiple refreshes at midnight will result in multiple day increments
            days += 1
        download_token = now  # Refresh download token to avoid stale download cache
        response += f'</div></div><br><a href="stats.csv?token{download_token}" class="downloadButton">Download</a><br><br>{month}-{mday}-{year} {(hour-12) if hour > 12 else hour }:{minute}:{second}<br>Runtime: {days} day(s) {hours} hour(s)<br><br><br><br><a href="delete.html" class="deleteButton">Delete</a></div>'+'\r\n'
        response += '</body></html>'+'\r\n\r\n'

    try:
        led.on()
        content_type = 'text/html'  # Default html
        max_age = 604800
        if not get_media_req:    # Toggle response type between html and favicon
            cl.send('HTTP/1.1 200 OK\r\nContent-type: text/html\r\nCache-Control: max-age=60\r\n\r\n')
            cl.send(response)
        else:
            print(f'Sending {request}')
            if contains_word(request, '/img/site.webmanifest'):
                content_type = 'application/manifest+json'
            elif contains_word(request, '/favicon.ico'):
                content_type = 'image/x-icon'
            elif contains_word(request.split('?')[0], f'/stats.csv'):
                print("Sending CSV File...")
                max_age = 0
                content_type = 'text/csv'
                try:
                    with open('stats.csv', 'rb') as f:
                        response = f.read()
                except OSError as e:
                    print(f'No csv found: {e}')
                response += '\r\n\r\n'
            elif contains_word(request, '/delete.html'):
                print('Removing stats.csv')
                try:
                    uos.remove('stats.csv')
                except OSError as e:
                    print(f'No csv found: {e}')
                print("Done.")
                max_age = 0
            else:
                content_type = 'image/png'
            cl.send(f'HTTP/1.1 200 OK\r\nContent-type: {content_type}\r\nAccept-Ranges: bytes\r\nCache-Control: max-age={max_age}\r\n\r\n')
            cl.send(response)
        get_media_req = False
        cl.close()
        print("Successfully Sent Request")
    except OSError as e:
        print(f'Error Sending Request: {e}')
        cl.close()

    led.off()
    recv_buf = ''   # Reset buffer
    response = ''   # Reset response
    request  = ''   # Reset request
    time.sleep_ms(1)
    print('\nListening for connections...\n')
