# LED Status Board Layout

Each household builds the same LED dashboard so everyone can interpret the status at a glance. The design assumes a 3D-printed or laser-cut faceplate with legends and a WS2812B LED strip mounted behind diffusers.

```
+------------------------------------------------------+
| Newcastle | Placerville | Citrus Heights | Roseville | Antelope |
|   LED1    |    LED2     |      LED3      |   LED4    |   LED5   |
+------------------------------------------------------+
```

## Physical Dimensions

- Faceplate: 280 mm × 70 mm × 3 mm acrylic.
- LED spacing: 50 mm center-to-center with 10 mm diffusers.
- Label font: 12 mm high sans-serif vinyl lettering for readability in low light.
- Mounting: Four M3 standoffs at the corners. Ensure the PCB or LED strip is 8–10 mm behind diffuser for soft glow.

## LED Wiring

1. Power the WS2812B strip from the regulated 5 V rail. Use a 470 Ω resistor on the data-in line and a 1000 µF capacitor across 5 V/GND at the strip to suppress surges.
2. Data line order corresponds to family locations:
   - Index 0 → Newcastle (HQ)
   - Index 1 → Placerville
   - Index 2 → Citrus Heights
   - Index 3 → Roseville
   - Index 4 → Antelope
3. Provide a 3-pin JST connector for quick replacement.

## LED Color Rules

| State | Color | Behavior |
| --- | --- | --- |
| Heartbeat received < 24 h | Solid green (`0x00FF00`) |
| SOS alert | Pulsing red (`0xFF0000`) at 1 Hz until acknowledged |
| No heartbeat ≥ 24 h | Solid yellow (`0xFFAA00`) |
| Pending handshake | Soft blue (`0x0030FF`) while establishing secure session |
| Admin maintenance mode | White (`0xFFFFFF`) |

## Additional Indicators

- Include a small bi-color LED near the buttons to show device-level status (green = connected, red = fault).
- Optional piezo buzzer can be added to sound when SOS is received (default silent mode for discretion).

