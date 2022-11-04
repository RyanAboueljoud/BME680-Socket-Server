import machine
import time
led = machine.Pin("LED", machine.Pin.OUT)
for x in range(0,3):
    led.on()
    time.sleep(0.25)
    led.off()
    time.sleep(0.25)
    