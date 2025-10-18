# Bill of Materials (BOM)

The table below captures the recommended hardware for each of the five nodes in the Newcastle Family System. Quantities are per-node unless otherwise noted. Choose either the 433 MHz or 915 MHz radio variant based on your local regulatory limits; all nodes must use the same band.

| Item | Qty | Notes |
| --- | --- | --- |
| TTGO T-Beam (ESP32 + LoRa + GPS) | 1 | Integrated ESP32 MCU with SX1276 LoRa radio. GPS enables optional time/position stamping. |
| 18650 Li-Ion cell (≥3000 mAh) | 2 | One primary + one spare. Provides 3–7 days runtime depending on duty cycle. |
| 18650 protected cell holder w/ leads | 1 | Prefer holders with built-in protection and mounting holes. |
| TP4056 Li-Ion charging module (USB-C) | 1 | For safe charging from solar or USB source. |
| 5 V / 2 A USB-C wall adapter | 1 | Indoor power/charging option. |
| 6 V / 3 W solar panel with USB-C regulator | 1 | Maintains battery during extended outages. |
| Step-up converter (3.3 V fixed) | 1 | Ensures stable supply for LEDs and sensors when battery sags. |
| Momentary push button ("I'm OK") | 1 | Latching cover recommended to avoid accidental presses. |
| Momentary push button ("SOS") | 1 | Red cap, requires ≥1.5 s long-press to trigger firmware logic. |
| 5× WS2812B (NeoPixel) RGB LEDs | 1 strip | One LED per family location; individually addressable. |
| Acrylic or polycarbonate LED faceplate | 1 | Printed labels for Newcastle, Placerville, Citrus Heights, Roseville, Antelope. |
| IP54-rated enclosure | 1 | Protects electronics; include gasketed feedthroughs for buttons and LEDs. |
| Waterproof grommets + cable glands | 4 | For LED strip, buttons, power, and solar leads. |
| On/off rocker switch | 1 | Master power disconnect. |
| PCB perfboard + standoffs | 1 | Mounting for buttons, level shifting, connectors. |
| JST-SM or Molex connectors | assorted | Quick-disconnects for LEDs and battery pack. |
| Ferrite beads / LC filter kit | 1 set | Reduces RF noise coupling into LEDs. |
| Heat-shrink tubing assortment | 1 | Weatherproofing connections. |
| Silicone-insulated wire (22 AWG) | 2 m | Power and signal wiring. |
| Spare fuses (500 mA resettable polyfuse) | 2 | Inline battery protection. |

## Optional Enhancements

- **Environmental sensors (BME280)** for temperature/humidity logging in future updates.
- **Vibration sensor (SW-420)** to detect enclosure tampering.
- **OLED status display** for textual diagnostics during setup.

## Procurement Notes

- Purchase all TTGO boards from the same batch to ensure identical radio modules.
- Calibrate battery safety by verifying TP4056 protection cutoff (~4.2 V).
- Verify regional LoRa frequency allocations before deployment.

