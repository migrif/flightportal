# flightportal-opensky

Displays live details of planes flying overhead on an Adafruit MatrixPortal M4 and 64x32 RGB LED matrix. When a plane enters your configured bounding box, a small plane animation flies across the display, followed by the callsign, altitude, speed and heading for each aircraft. Multiple planes are cycled through one by one, with a count shown first.

> Based on the original [flightportal](https://github.com/smartbutnot/flightportal) project by smartbutnot. This version updates it to use the OpenSky Network API (FlightRadar24 no longer works on embedded clients) and targets CircuitPython 10.

https://user-images.githubusercontent.com/103124527/206902629-1f31bd41-d8a8-415e-a35a-625efb20b3d6.MOV

*Video sped up — speeds and delays are all configurable in code.py*

---

## What's different from the original

- **OpenSky Network API** instead of FlightRadar24 (FR24's HTTPS endpoint is no longer compatible with the ESP32 co-processor on the MatrixPortal)
- **CircuitPython 10** compatibility — uses `display.root_group` instead of the removed `display.show()`
- **Multiple planes** — cycles through all airborne aircraft in your bounding box, showing a count first
- **Configuration via `settings.toml`** instead of the old `secrets.py` format
- **Watchdog improvements** — feeds the watchdog during all long operations to prevent unexpected resets
- **ESP32 auto-recovery** — automatically resets and reconnects the ESP32 co-processor if it becomes unresponsive

---

## Hardware

1. [Adafruit MatrixPortal M4](https://www.adafruit.com/product/4745)
2. P4 64x32 RGB matrix panel — available from Aliexpress
3. [3D printed case](https://www.thingiverse.com/thing:5701517)
4. [Adafruit acrylic diffuser](https://www.adafruit.com/product/4749)
5. 6x M3 screws, approximately 8mm long
6. Optional: [Uglu dashes](https://www.protapes.com/products/uglu-600-dashes-sheets) to secure the diffuser

---

## Setup

### 1. Prep the MatrixPortal

Follow the [official Adafruit guide](https://learn.adafruit.com/adafruit-matrixportal-m4/prep-the-matrixportal) to get CircuitPython installed.

### 2. Update ESP32 firmware and bootloader

This is important — old firmware causes connection instability:

- Update the ESP32 co-processor firmware to **1.7.7 or later**
- Update the MatrixPortal bootloader to **4.0 or later** if you experience ESP32 crashes

### 3. Install libraries

Copy the following into the `/lib` folder on your CIRCUITPY drive. Get them from the [CircuitPython library bundle](https://circuitpython.org/libraries) — make sure the bundle version matches your CircuitPython version.

```
adafruit_connection_manager.mpy
adafruit_display_text/
adafruit_esp32spi/
adafruit_matrixportal/
adafruit_requests.mpy
```

### 4. Configure settings.toml

Create a `settings.toml` file in the root of your CIRCUITPY drive:

```toml
CIRCUITPY_WIFI_SSID = "your_wifi_network"
CIRCUITPY_WIFI_PASSWORD = "your_wifi_password"

# Bounding box for OpenSky: lamin,lomin,lamax,lomax
# (south lat, west lon, north lat, east lon)
# Example below is roughly Christchurch, NZ
bounds_box = "-44.0,172.0,-43.0,173.0"

# Enable or disable the status NeoPixel LED
status_leds = "True"
```

> **Bounds box format:** OpenSky expects `lamin,lomin,lamax,lomax` — that's south latitude first, then west longitude, then north latitude, then east longitude. Getting this wrong will return no results.

### 5. Copy code.py

Copy `code.py` to the root of your CIRCUITPY drive. It will start running automatically.

---

## Display layout

| Row | Short display | Notes |
|-----|--------------|-------|
| 1 | Callsign | e.g. `ANZ555` |
| 2 | Altitude | e.g. `35000ft` |
| 3 | Speed + Heading | e.g. `480kt 270d` |

When multiple planes are found, a count is shown first (e.g. `3 planes nearby`) then each plane cycles through with its own animation.

---

## Configuration

At the top of `code.py` you can adjust:

```python
QUERY_DELAY = 30                    # Seconds between OpenSky queries
PAUSE_BETWEEN_LABEL_SCROLLING = 3   # Seconds between each row scrolling
PLANE_SPEED = 0.02                  # Seconds per pixel for plane animation (lower = faster)
TEXT_SPEED = 0.04                   # Seconds per pixel for text scrolling
ROW_ONE_COLOUR = 0xEE82EE           # Callsign colour
ROW_TWO_COLOUR = 0x4B0082           # Altitude colour
ROW_THREE_COLOUR = 0xFFA500         # Speed/heading colour
```

---

## OpenSky API rate limits

The anonymous OpenSky API allows one request per 10 seconds. With the default `QUERY_DELAY` of 30 seconds you are well within this limit. See the [OpenSky API docs](https://openskynetwork.github.io/opensky-api/rest.html#limitations) for full details. Creating a free OpenSky account gives you a higher rate limit if needed.

---

## Troubleshooting

**ESP32 not responding**
Update the ESP32 firmware to 1.7.7+ and the bootloader to 4.0+. The script will automatically reset and reconnect the ESP32 if it becomes unresponsive.

**No planes showing**
Check your `bounds_box` coordinates are in the correct order (`lamin,lomin,lamax,lomax`). Verify your box at: `https://opensky-network.org/api/states/all?lamin=<lamin>&lomin=<lomin>&lamax=<lamax>&lomax=<lomax>`

**`AttributeError: .show(x) removed`**
You are on CircuitPython 9 or later. This version of the code already uses `root_group` so make sure you have the latest `code.py`.

**`TypeError: unsupported types for __add__: 'str', 'NoneType'`**
Your `settings.toml` is missing or has a formatting issue. Make sure the file is in the root of CIRCUITPY and all four entries are present.


Disclosure. ClaudeCode was used for this project & reademe.
