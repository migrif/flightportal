import os
import time
import terminalio
from adafruit_matrixportal.matrixportal import MatrixPortal
import adafruit_connection_manager
import board
import json

import adafruit_display_text.label
import displayio
import gc
import random

import busio
from digitalio import DigitalInOut
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests
from microcontroller import watchdog as w
from watchdog import WatchDogMode

w.timeout = 16
w.mode = WatchDogMode.RESET

FONT = terminalio.FONT

QUERY_DELAY = 30

ROW_ONE_COLOUR = 0xEE82EE
ROW_TWO_COLOUR = 0x4B0082
ROW_THREE_COLOUR = 0xFFA500
PLANE_COLOUR = 0x4B0082
PAUSE_BETWEEN_LABEL_SCROLLING = 3
PLANE_SPEED = 0.02
TEXT_SPEED = 0.04

ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

# Bounding box from settings.toml - OpenSky uses lamin,lomin,lamax,lomax
# bounds_box should be "lamin,lomin,lamax,lomax" e.g. "51.4,-0.3,51.6,-0.1"
BOUNDS_BOX = os.getenv("bounds_box")
bounds = BOUNDS_BOX.split(",")
FLIGHT_SEARCH_URL = (
    "http://opensky-network.org/api/states/all"
    "?lamin=" + bounds[0] +
    "&lomin=" + bounds[1] +
    "&lamax=" + bounds[2] +
    "&lomax=" + bounds[3]
)

# OpenSky state vector indices
# [icao24, callsign, origin_country, time_position, last_contact,
#  longitude, latitude, baro_altitude, on_ground, velocity,
#  true_track, vertical_rate, sensors, geo_altitude, squawk, spi, position_source]
OPENSKY_CALLSIGN = 1
OPENSKY_COUNTRY  = 2
OPENSKY_LON      = 5
OPENSKY_LAT      = 6
OPENSKY_ALT      = 7
OPENSKY_ON_GROUND= 8
OPENSKY_VELOCITY = 9
OPENSKY_HEADING  = 10

status_led_value = os.getenv("status_leds", "True").lower()
USE_LEDS = status_led_value in ["true", "1", "yes", "on"]

# Plain HTTP headers - no HTTPS needed for OpenSky
rheaders = {
    "Accept": "application/json"
}

esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
radio = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

matrixportal = MatrixPortal(
    esp=radio,
    rotation=0,
    debug=False
)

planeBmp = displayio.Bitmap(12, 12, 2)
planePalette = displayio.Palette(2)
planePalette[1] = PLANE_COLOUR
planePalette[0] = 0x000000
planeBmp[6,0]=planeBmp[6,1]=planeBmp[5,1]=planeBmp[4,2]=planeBmp[5,2]=planeBmp[6,2]=1
planeBmp[9,3]=planeBmp[5,3]=planeBmp[4,3]=planeBmp[3,3]=1
planeBmp[1,4]=planeBmp[2,4]=planeBmp[3,4]=planeBmp[4,4]=planeBmp[5,4]=planeBmp[6,4]=planeBmp[7,4]=planeBmp[8,4]=planeBmp[9,4]=1
planeBmp[1,5]=planeBmp[2,5]=planeBmp[3,5]=planeBmp[4,5]=planeBmp[5,5]=planeBmp[6,5]=planeBmp[7,5]=planeBmp[8,5]=planeBmp[9,5]=1
planeBmp[9,6]=planeBmp[5,6]=planeBmp[4,6]=planeBmp[3,6]=1
planeBmp[6,9]=planeBmp[6,8]=planeBmp[5,8]=planeBmp[4,7]=planeBmp[5,7]=planeBmp[6,7]=1
planeTg = displayio.TileGrid(planeBmp, pixel_shader=planePalette)
planeG = displayio.Group(x=matrixportal.display.width+12, y=10)
planeG.append(planeTg)

label1 = adafruit_display_text.label.Label(FONT, color=ROW_ONE_COLOUR, text="")
label1.x = 1
label1.y = 4

label2 = adafruit_display_text.label.Label(FONT, color=ROW_TWO_COLOUR, text="")
label2.x = 1
label2.y = 15

label3 = adafruit_display_text.label.Label(FONT, color=ROW_THREE_COLOUR, text="")
label3.x = 1
label3.y = 25

label1_short = ''
label1_long = ''
label2_short = ''
label2_long = ''
label3_short = ''
label3_long = ''

g = displayio.Group()
g.append(label1)
g.append(label2)
g.append(label3)
matrixportal.display.root_group = g


def plane_animation():
    # Pick a random bright colour for the plane each time
    planePalette[1] = random.randint(0x111111, 0xFFFFFF)
    matrixportal.display.root_group = planeG
    for i in range(matrixportal.display.width+24, -12, -1):
        planeG.x = i
        w.feed()
        time.sleep(PLANE_SPEED)


def scroll(line):
    line.x = matrixportal.display.width
    for i in range(matrixportal.display.width+1, 0-line.bounding_box[2], -1):
        line.x = i
        w.feed()
        time.sleep(TEXT_SPEED)


def display_flight():
    matrixportal.display.root_group = g
    label1.x = 1
    label2.x = 1
    label3.x = 1
    label1.text = label1_short
    label2.text = label2_short
    label3.text = label3_short
    w.feed()


def clear_flight():
    label1.text = label2.text = label3.text = ""


def reset_esp():
    print("Resetting ESP32...")
    radio.reset()
    time.sleep(3)
    w.feed()


def checkConnection():
    print("Connecting to AP...")
    while not radio.is_connected:
        try:
            w.feed()
            radio.connect_AP(ssid, password)
        except (RuntimeError, ConnectionError) as e:
            print("could not connect to AP, retrying: ", e)
            reset_esp()
            continue
    print("Connected")
    set_led_color(status_light, 'green')


def reconnect():
    reset_esp()
    set_led_color(status_light, 'yellow')
    checkConnection()
    global requests
    pool = adafruit_connection_manager.get_radio_socketpool(radio)
    ssl_context = adafruit_connection_manager.get_radio_ssl_context(radio)
    requests = adafruit_requests.Session(pool, ssl_context)


# Query OpenSky and return list of all airborne aircraft state vectors, or False
def get_flights():
    try:
        with requests.get(url=FLIGHT_SEARCH_URL, headers=rheaders) as response:
            data = response.json()
            states = data.get("states", None)
            if states and len(states) > 0:
                airborne = [s for s in states if not s[OPENSKY_ON_GROUND]]
                if airborne:
                    return airborne
            return False
    except (RuntimeError, OSError, TimeoutError) as e:
        print("get_flights error: ", e)
        reconnect()
        return False


# Parse an OpenSky state vector into display labels
def get_route(callsign):
    """Look up route by callsign from adsbdb.com, returns 'ORG-DST' or None"""
    try:
        url = "http://api.adsbdb.com/v0/callsign/" + callsign
        with requests.get(url=url, headers=rheaders) as response:
            if response.status_code == 200:
                data = response.json()
                w.feed()
                flightroute = data.get("response", {}).get("flightroute", None)
                if flightroute:
                    origin = flightroute.get("origin", {}).get("iata_code", None)
                    dest   = flightroute.get("destination", {}).get("iata_code", None)
                    if origin and dest:
                        return origin + "-" + dest
    except (RuntimeError, OSError, TimeoutError, KeyError, ValueError, TypeError) as e:
        print("Route lookup error: ", e)
    return None


def parse_flight(state):
    global label1_short, label1_long
    global label2_short, label2_long
    global label3_short, label3_long

    try:
        callsign = str(state[OPENSKY_CALLSIGN]).strip() if state[OPENSKY_CALLSIGN] else "Unknown"
        country  = str(state[OPENSKY_COUNTRY]).strip() if state[OPENSKY_COUNTRY] else "Unknown"
        alt_m    = state[OPENSKY_ALT]
        velocity = state[OPENSKY_VELOCITY]
        heading  = state[OPENSKY_HEADING]

        # Convert altitude to feet, speed to knots
        alt_ft  = int(alt_m * 3.28084) if alt_m else 0
        spd_kts = int(velocity * 1.94384) if velocity else 0
        hdg     = int(heading) if heading else 0

        print("Flight: " + callsign + " from " + country)
        print("Alt: " + str(alt_ft) + "ft  Spd: " + str(spd_kts) + "kts  Hdg: " + str(hdg))

        label1_short = callsign
        label1_long  = callsign
        label2_short = str(alt_ft) + "ft"
        label2_long  = str(alt_ft) + "ft"
        label3_short = str(spd_kts) + "kt " + str(hdg) + "d"
        label3_long  = str(spd_kts) + "kt " + str(hdg) + "d"

    except (KeyError, ValueError, TypeError) as e:
        print("Parse error: ", e)
        return False

    return True

def set_led_color(status_light, color_name):
    if not USE_LEDS or status_light is None:
        color_name = "off"
    colors = {
        'red':    (255, 0, 0),
        'green':  (0, 255, 0),
        'blue':   (0, 0, 255),
        'yellow': (255, 255, 0),
        'purple': (255, 0, 255),
        'white':  (255, 255, 255),
        'off':    (0, 0, 0)
    }
    if color_name.lower() in colors:
        status_light[0] = colors[color_name.lower()]
        status_light.show()
        return True
    return False


# --- Main ---
set_led_color(status_light, 'yellow')
checkConnection()

pool = adafruit_connection_manager.get_radio_socketpool(radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(radio)
requests = adafruit_requests.Session(pool, ssl_context)

while True:
    if not radio.is_connected:
        set_led_color(status_light, 'yellow')
        checkConnection()

    w.feed()

    states = get_flights()
    w.feed()

    if states:
        count = len(states)
        print(str(count) + " plane(s) found")

        # Show count on screen briefly
        clear_flight()
        label1.text = str(count) + " plane" + ("s" if count > 1 else "") + " nearby"
        label2.text = "overhead"
        w.feed()
        time.sleep(3)

        # Cycle through each plane
        for state in states:
            callsign = str(state[OPENSKY_CALLSIGN]).strip() if state[OPENSKY_CALLSIGN] else "Unknown"
            print("Showing: " + callsign)
            clear_flight()
            if parse_flight(state):
                gc.collect()
                plane_animation()
                display_flight()
                for _ in range(2):
                    w.feed()
                    time.sleep(5)
            else:
                print("Error parsing flight, skipping")
            w.feed()
    else:
        clear_flight()

    time.sleep(5)
    w.feed()

    for i in range(0, QUERY_DELAY, 5):
        time.sleep(5)
        w.feed()

    gc.collect()
