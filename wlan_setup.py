import network
import time
from machine import Pin

led = Pin("LED", Pin.OUT)

# Initialize and connect wireless lan
def connect():
    led.on()
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
    if network.WLAN().status() is not network.STAT_GOT_IP:
        with open("wifi_info.txt", 'r') as f:   # WLAN cred format: SSID\nPW
            wifi_info = f.readlines()
        ssid = wifi_info[0].strip()
        password = wifi_info[1].strip()
        wlan.connect(ssid, password)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        led.on()
        time.sleep(1)
        led.off()

    led.on()
    if wlan.status() != network.STAT_GOT_IP:
        raise RuntimeError('network connection failed')
    else:
        sta_if = network.WLAN(network.STA_IF)
        print(f'\nHost Address: {sta_if.ifconfig()[0]}')  # Print local IP
        print()
    led.off()


# Check if network is active
def isactive():
    return network.WLAN().active()


# Check if network is connected
def isconnected():
    return network.WLAN().isconnected()


# Check network status
def status():
    return network.WLAN().status()

def getIp():
    return network.WLAN(network.STA_IF).ifconfig()[0]
