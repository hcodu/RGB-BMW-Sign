import os
import time
import ssl
import wifi
import socketpool
import board
import busio
import neopixel
from digitalio import DigitalInOut

from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.animation.colorcycle import ColorCycle
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.customcolorchase import CustomColorChase
from adafruit_led_animation.animation.Rainbow import Rainbow


from adafruit_led_animation.color import RED, BLUE, WHITE

import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

# ----- Global state variables
LIGHTS_ON = True
MODE = "bmw"
COLOR = 0x6A0DAD
M_END_PIXEL_INDEX = 53
SLASH1_END_PIXEL_INDEX = 81
SLASH2_END_PIXEL_INDEX = 106
SLASH3_END_PIXEL_INDEX = 128

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# ----- NeoPixel setup
ORDER = neopixel.GRB
pixel_pin = board.GP0
num_pixels = 180
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, auto_write = False)    # Pico Wiring
pixels.brightness = 0.2

pulse_red = Pulse(pixels, speed=0.1, period=4, color=RED)
pulse_blue = Pulse(pixels, speed=0.1, period=4, color=BLUE)
pulse_white = Pulse(pixels, speed=0.1, period=4, color=WHITE)

comet_red = Comet(pixels, speed=0.05, color=RED, tail_length=20, ring = True)
comet_blue = Comet(pixels, speed=0.05, color=BLUE, tail_length=20, ring = True)
comet_white = Comet(pixels, speed=0.05, color=WHITE, tail_length=20, ring = True)

comet_animations = AnimationSequence(
    comet_red, comet_blue, comet_white, advance_interval=9.1, auto_clear=True, auto_reset = True
)
pulse_animations = AnimationSequence(
    pulse_red, pulse_blue, pulse_white, advance_interval = 4, auto_clear=False, auto_reset = True,
)

rainbow = Rainbow(pixels, speed=0.1, period=5, step=0.5)

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
def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")
def on_message(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    global LIGHTS_ON, MODE, COLOR
    
    if feed_id == "pico-feeed":
        if payload == "true":
            LIGHTS_ON = True
        if payload == "false":
            LIGHTS_ON = False
    
    if feed_id == "pico-mode-feed":
        if(payload[0:1] == "#"):
            MODE = "solid"
            payload = "0x" + payload[1:7]
            hex_int = int(payload, 16)
            COLOR = hex_int    
        else:    
            MODE = payload
        
    if feed_id == "pico-brightness-feed":
        pixels.brightness = int(payload) / 100
        print("TESTTT")
    
    if LIGHTS_ON:
        if MODE == "bmw":
            bmw_colors()      
        if MODE == "solid":
            pixels.fill(COLOR)
            pixels.show()

    if not LIGHTS_ON:
        pixels.fill((0, 0, 0))
        pixels.show()
    
           
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

# ----- Connect to Adafruit IO MQTT server, subscribe to 'pico-feeed', 'pico-mode-feed', and 'pico-brightness-feed' 
io.connect()
io.subscribe('pico-feeed')
io.subscribe('pico-mode-feed')
io.subscribe('pico-brightness-feed')


def bmw_colors():
    pixels.fill((0,0,0))
    for i in range(M_END_PIXEL_INDEX):
        pixels[i] = (255, 255, 255)
        pixels.show()
        time.sleep(0.03)
    for i in range(SLASH1_END_PIXEL_INDEX - M_END_PIXEL_INDEX):
        pixels[i + M_END_PIXEL_INDEX] = (255, 0, 0)
        pixels.show()
        time.sleep(0.03)
    for i in range(SLASH2_END_PIXEL_INDEX - SLASH1_END_PIXEL_INDEX):
        pixels[i + SLASH1_END_PIXEL_INDEX] = (0, 210, 255)
        pixels.show()
        time.sleep(0.03)
    for i in range(SLASH3_END_PIXEL_INDEX - SLASH2_END_PIXEL_INDEX):
        pixels[i + SLASH2_END_PIXEL_INDEX] = (0, 0, 255)
        pixels.show()
        time.sleep(0.03)
        
bmw_colors()

while True:    
    
    
    if(LIGHTS_ON):
        if(MODE == "pulse"):    
            pulse_animations.animate()
        if(MODE == "comet"):
            comet_animations.animate()   
        if(MODE == "rgb"):
            rainbow.animate()    
    try:
        io.loop(0.01)
    except (ValueError, RuntimeError, Exception) as e:
        print("Failed to loop MQTT, attempting to reconnect \n", e)


    
    # print("MODE: " + MODE + " ON?: " + str(LIGHTS_ON))
