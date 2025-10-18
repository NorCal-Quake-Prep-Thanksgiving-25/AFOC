# Firmware Overview

The firmware targets the TTGO T-Beam (ESP32 + SX1276). It is written using PlatformIO (Arduino framework) and implements secure mesh messaging, button input, and LED control for the Newcastle Family System.

## Features

- AES-GCM encrypted LoRa frames with per-node keys.
- Mesh routing with hop-based forwarding and duplicate suppression.
- Daily status evaluation to set LED colors (green, yellow, red).
- Long-press SOS detection with audible/visual alerts.
- Low-power heartbeat mode when battery voltage drops below threshold.

## Building

1. Install [PlatformIO Core](https://docs.platformio.org/en/latest/core/index.html).
2. From repo root, run:
   ```bash
   cd firmware
   pio run
   ```
3. To flash a connected device:
   ```bash
   pio run --target upload
   ```
4. View serial logs at 115200 baud:
   ```bash
   pio device monitor
   ```

## Configuration

Key parameters are defined in `src/main.cpp`:

- `g_nodeId`: Default 32-bit ID for this build target (override via provisioning).
- `FREQUENCY`: LoRa center frequency (433E6 or 915E6).
- `HB_INTERVAL_MIN`: Heartbeat interval minutes.
- `SOS_HOLD_MS`: Duration required to confirm SOS.

Secrets (keys, provisioning data) are loaded at runtime from NVS; do **not** hardcode production keys.

## Provisioning Keys & Node IDs

Use `tools/provision.py` together with the running firmware to load secure material over USB:

```bash
pip install pyserial
python tools/provision.py /dev/ttyUSB0 --node-id 0x4E435C01 --family-key <64_hex_chars>
```

Run the script once per node, substituting the appropriate `--node-id` constant from `NODE_MAP` in `src/main.cpp`. The script writes the family root key, per-node key (derived if not provided), and node ID into ESP32 preferences. Finish with the `COM` command automatically issued by the tool to derive a fresh session key.

## Directory Layout

```
firmware/
├── platformio.ini          # PlatformIO project config
├── README.md               # This file
└── src/
    └── main.cpp            # Arduino sketch entry point
```

