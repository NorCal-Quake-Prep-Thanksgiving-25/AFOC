# Newcastle Family Offline Safety Mesh

This repository contains the design package and reference firmware for an encrypted, LoRa-based family safety network that operates without cellular or internet infrastructure. It covers five Northern California locations: Newcastle (HQ), Placerville, Citrus Heights, Roseville, and Antelope.

## Repository Contents

- `docs/bom.md` – Hardware bill of materials for each household node.
- `docs/secure_protocol.md` – Authenticated mesh communication protocol.
- `docs/led_board_layout.md` – LED dashboard layout and wiring rules.
- `docs/setup_guide.md` – Step-by-step provisioning and deployment instructions.
- `docs/dashboard_template.md` – Printable analog status board.
- `docs/test_plan.md` – Validation checklist for reliability and coverage.
- `firmware/` – PlatformIO project for TTGO T-Beam nodes, including encrypted messaging, button handling, and LED control.
- `tools/provision.py` – Serial provisioning utility for loading keys and node IDs.

## Getting Started

1. Review the bill of materials and procure hardware for all five locations.
2. Assemble and provision each node following the setup guide.
3. Flash the firmware using PlatformIO (`cd firmware && pio run --target upload`).
4. Execute the test plan to validate coverage, power, and fail-safe behavior.

The system enables each family member to broadcast "I'm OK" or SOS alerts, while every home displays real-time status via synchronized LED dashboards. If a location fails to check in within 24 hours, the corresponding indicator automatically turns yellow to prompt a welfare check.

