import os
import time
import ssl
import wifi
import socketpool
import board
import busio
import neopixel
from digitalio import DigitalInOut

import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

# ----- Global state variables
LIGHTS_ON = True
MODE = "bmw"


try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# ----- NeoPixel setup
ORDER = neopixel.GRB
pixel_pin = board.GP0
num_pixels = 180
pixels = neopixel.NeoPixel(pixel_pin, num_pixels)    # Pico Wiring
pixels.brightness = 0.2

# ----- Socketpool, esp, and spi setup
pool = socketpool.SocketPool(wifi.radio)
spi = busio.SPI(board.GP10, board.GP11, board.GP12)
esp32_cs = DigitalInOut(board.GP13)
esp32_ready = DigitalInOut(board.GP14)
esp32_reset = DigitalInOut(board.GP15)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# ----- Connects to WIFI and prints ipv4 address
print("\n Connecting to wifi!")
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("My IP address is", wifi.radio.ipv4_address)

# ----- Methods for handling Adafruit IO MQTT traffic
def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    print("Connected to Adafruit IO!  Listening for feed changes...")
def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))
def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))
# pylint: disable=unused-argument
def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")
# pylint: disable=unused-argument
def on_message(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    global LIGHTS_ON, MODE
    
    if feed_id == "pico-feeed":
        if payload == "true":
            LIGHTS_ON = True
        if payload == "false":
            LIGHTS_ON = False
    
    if feed_id == "pico-mode-feed":
        MODE = payload
        
    if feed_id == "pico-brightness-feed":
        pixels.brightness = int(payload) / 100
        print("TESTTT")
    
    if LIGHTS_ON:
        if MODE == "bmw":
            bmw_colors()
        if MODE == "rgb":
            rainbow_cycle(0.0001)

    if not LIGHTS_ON:
        pixels.fill((0, 0, 0))
    
           
    print("Feed {0} received new value: {1}".format(feed_id, payload))

# ----- Setup and initalize MQTT and Adafruit IO MQTT 
MQTT.set_socket(socket, esp)
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=1883,
    username=secrets['aio_username'],
    password=secrets['aio_key'],
    socket_pool = pool,
    ssl_context = ssl.create_default_context(),
)
io = IO_MQTT(mqtt_client)

# ----- Pass IO methods to client
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe
io.on_unsubscribe = unsubscribe
io.on_message = on_message

# ----- Connect to Adafruit IO MQTT server, subscribe to 'pico feeed' and 'pico-mode-feed' 
io.connect()
io.subscribe('pico-feeed')
io.subscribe('pico-mode-feed')
io.subscribe('pico-brightness-feed')

# ----- Methods for doing a rainbow wave RGB effect and BMW RGB Effect
def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)
def rainbow_cycle(wait):
    for j in range(255):
        # print("J + " + str(j))
        for i in range(180):
            # print("I + " + str(i))
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(pixel_index & 255)
        pixels.show()
    print("FINISHED")
def bmw_colors():
    for i in range(57):
        pixels[i] = (255, 255, 255)
        time.sleep(0.03)
    for i in range(40):
        pixels[i + 57] = (255, 0, 0)
        time.sleep(0.03)
    for i in range(40):
        pixels[i + 97] = (0,0,255)
    for i in range(40):
        pixels[i + 137] = (0,150,255)

bmw_colors()

while True:    
    try:
        io.loop()
    except (ValueError, RuntimeError, Exception) as e:
        print("Failed to loop MQTT, attempting to reconnect \n", e)

        try:
            io.reconnect()
        except(ValueError, RuntimeError, Exception) as e:
            print("Failed to reconnect to MQTT, reconnecting \n", e)
    
    print("MODE: " + MODE + " ON?: " + str(LIGHTS_ON))
    # time.sleep(1)