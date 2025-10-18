# Setup Guide

Follow these steps to provision and deploy each Newcastle Family System node. Complete tasks in order to guarantee secure, synchronized communication.

## 1. Bench Preparation

1. **Flash firmware** onto each TTGO T-Beam using PlatformIO or the Arduino IDE (see `firmware/README.md`).
2. **Label hardware** with permanent marker: Newcastle, Placerville, Citrus Heights, Roseville, Antelope.
3. **Inspect batteries** for damage and charge them to 4.1 V using the TP4056 charger.

## 2. Cryptographic Provisioning

1. Connect the node via USB and open a serial terminal at 115200 baud.
2. Use the provisioning tool (`python tools/provision.py`) to load:
   - `node_id`
   - Public/private keypair
   - Derived `K_node[i]`
3. Verify the device prints `PROVISION OK`. If not, repeat after factory reset (`hold OK button while powering on`).

## 3. Hardware Assembly

1. Mount the TTGO board on standoffs inside the enclosure.
2. Install the WS2812B LED strip behind the faceplate following the wiring order in `docs/led_board_layout.md`.
3. Wire buttons: connect to GPIOs defined in firmware (`GPIO34` for OK, `GPIO35` for SOS) with pull-down resistors.
4. Add the master power switch inline with the battery positive lead.
5. Connect solar panel to TP4056 input; route regulated 5 V to the board via the step-up converter.

## 4. Functional Testing (Indoors)

1. Power on two nodes.
2. Ensure both enter `TIME SYNC` mode and negotiate handshake (blue LEDs glow briefly).
3. Press "I'm OK" on one node. All connected dashboards should turn the corresponding LED green.
4. Hold "SOS" for 2 seconds. Confirm all dashboards pulse red for that location and that the serial console logs `SOS BROADCAST`.

## 5. Field Deployment

1. Place each enclosure near an exterior window or attic with minimal obstructions.
2. Mount solar panel outdoors facing south with 30–40° tilt for Northern California latitude.
3. Verify LoRa signal strength (RSSI > -110 dBm) by observing diagnostic logs (`press admin button 3× quickly`).
4. Log the installed location, GPS coordinates, and deployment date in the family binder.

## 6. Daily Use

- Every morning, tap "I'm OK". The system automatically transitions to yellow after 24 hours of silence.
- If SOS is triggered, reset only after the situation is resolved by pressing the concealed admin button and entering the PIN (default `4268`).
- Keep batteries charged by leaving the USB-C supply connected whenever grid power is available.

## 7. Maintenance

- Run a full system test monthly (simulate an SOS and verify mesh paths).
- Replace batteries annually or when capacity drops below 70% (measured during maintenance).
- Update firmware biannually. Apply over USB with the secure bootloader; ensure signatures match before confirming upgrade.

