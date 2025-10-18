# Test Plan

This plan verifies reliability, coverage, and fail-safe behavior of the Newcastle Family System. Execute tests quarterly or after firmware updates.

## 1. Unit Tests (Bench)

| Test | Procedure | Expected Result |
| --- | --- | --- |
| Button debounce | Trigger 20 rapid taps on each button while logging serial output. | No false triggers; at most one event per press. |
| LED mapping | Issue command `diag led-cycle` over serial. | LEDs advance in Newcastle→Placerville→Citrus Heights→Roseville→Antelope order. |
| Crypto handshake | Run `diag handshake` to pair with a test node. | Session key established, no auth failures. |
| Battery cutoff | Simulate low voltage (3.3 V). | Device enters low-power heartbeat mode and logs `LOW BAT`. |

## 2. Integration Tests (Indoor Mesh)

1. Power all five nodes in the same room.
2. Run `diag mesh-map` to confirm each node sees at least two neighbours with RSSI > -90 dBm.
3. Send `I'm OK` from each node sequentially; verify LED change propagates within 5 seconds.
4. Trigger SOS on Roseville node; confirm all other nodes pulse red and produce audible alert (if enabled).
5. Disconnect Newcastle hub and repeat steps 3–4 to ensure mesh reroutes through Placerville.

## 3. Range & Coverage Tests

- **Static Range**: Place Newcastle at HQ, move Placerville node outward in 0.5-mile increments up to 5 miles. Record RSSI and packet success ratio (PSR) for 50 pings per distance.
- **Urban Penetration**: Operate Citrus Heights node inside a multi-story building; measure PSR with roof-mounted antenna vs. indoor window placement.
- **Suburban Loop**: Drive Roseville and Antelope nodes around neighbourhood cul-de-sacs; log GPS track and coverage gaps.

## 4. Endurance / Battery Tests

- Run each node on battery only with 15-minute heartbeat interval and nightly SOS drill. Expect ≥72 hours runtime.
- Verify solar recharge by leaving node outdoors for full day; measure battery voltage recovery (>4.0 V).

## 5. Failure Simulations

| Scenario | Method | Expected Behavior |
| --- | --- | --- |
| Node offline | Remove power from Citrus Heights node. | All dashboards show yellow within 24 h; mesh reroutes around gap. |
| Tamper attempt | Send forged packet with wrong HMAC. | Receiving node logs `AUTH FAIL`, ignores packet, increases tamper counter. |
| Clock drift | Set Antelope node clock +10 min. | Time sync frame from Newcastle corrects within next cycle. |
| Packet storm | Flood Newcastle node with 20 pings/min. | Rate limiter drops excess; system remains responsive. |

## 6. Documentation & Reporting

- Record all measurements in shared binder and digital log (USB drive stored at HQ).
- Update maintenance checklist with any repairs or part replacements.
- After each quarterly test, conduct a family tabletop drill to review findings.

