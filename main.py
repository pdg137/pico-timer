import sh1106
from machine import SPI, Pin
from time import ticks_us, sleep_ms
from bootsel import read_bootsel

led = Pin(25, Pin.OUT)
sck = Pin(14)
mosi = Pin(15)
dc = Pin(17)
res = Pin(16)

spi = SPI(id=1, baudrate=4000000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=None)
display = sh1106.SH1106_SPI(128, 64, spi, dc, res=res, rotate=180)

sensor_power = Pin(27, Pin.OUT, value=1)
sensor = Pin(26, Pin.IN)

STATE_COLLECTING = 0
STATE_STOPPING = 1
STATE_PAUSED = 2
STATE_STARTING = 3

state = STATE_COLLECTING
last_transition = 0

def reset():
    global history
    history = [0]*128
    update()
    
def check_button():
    global state, STATE_COLLECTING, STATE_STOPPING, STATE_PAUSED, STATE_STARTING
    global last_valid, last_transition
    pressed = read_bootsel() == 0
    new_state = state
    if state == STATE_COLLECTING:
        if pressed:
            new_state = STATE_STOPPING
    elif state == STATE_STOPPING:
        if not pressed:
            new_state = STATE_PAUSED
        elif ticks_us() - last_transition > 1000000:
            reset()
    elif state == STATE_PAUSED:
        if pressed:
            new_state = STATE_STARTING
    elif state == STATE_STARTING:
        if not pressed:
            new_state = STATE_COLLECTING
        elif ticks_us() - last_transition > 1000000:
            reset()
    
    if state != new_state:
        state = new_state
        last_transition = ticks_us()
        last_valid = False
        update()

def update():
    global history, state, STATE_COLLECTING, STATE_STOPPING, STATE_PAUSED, STATE_STARTING
    display.fill(0)
    
    if state == STATE_COLLECTING:
        display.text("Collecting data", 0, 0)
    elif state == STATE_STOPPING:
        if history[127] != 0:
            display.text("Hold to erase...", 0, 0)
        else:
            display.text("Data cleared.", 0, 0)
    elif state == STATE_PAUSED:
        display.text("** Paused **", 0, 0)
    elif state == STATE_STARTING:
        if history[127] != 0:
            display.text("Hold to erase...", 0, 0)
        else:
            display.text("Data cleared.", 0, 0)
    
    min_val = history[127]
    max_val = history[127]
    total = 0
    count = 0
    for val in history:
        if val != 0:
            min_val = min(val, min_val)
            max_val = max(val, max_val)
            total += val
            count += 1
    if count != 0:
        mean = total / count
    else:
        mean = 0
    
    msg = "Last: {:.02f} ms".format(history[127]/1000)
    display.text(msg, 0, 8)
    msg = "Mean: {:.02f} ms".format(mean/1000)
    display.text(msg, 0, 16)
    
    if min_val != max_val:
        for x in range(128):
            if history[x] != 0:
                y = round((history[x]-min_val)/(max_val-min_val)*32)
                display.pixel(x, 64-y, 1)
    
    max_s = "{:.02f}".format(max_val/1000)
    min_s = "{:.02f}".format(min_val/1000)
    display.text(max_s, 0, 32)
    display.text(min_s, 0, 56)
    
    display.show()

history = [0]*128
last = 0
last_valid = False

while True:
    update()
    
    while sensor() == 0:
        led(0)
        check_button()
    while sensor() == 1:
        led(0)
        check_button()
    sleep_ms(50) # debounce
    while sensor() == 0:
        led(1)
        check_button()
    while sensor() == 1:
        led(1)
        check_button()
    
    if state == STATE_COLLECTING:
        now = ticks_us()
        elapsed = now - last
    
        if last_valid:
            history.append(elapsed)
            history.pop(0)
            
        last = now
        last_valid = True
    else:
        last_valid = False
