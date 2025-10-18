# Secure Communication Protocol

This document defines the authenticated mesh protocol used by the Newcastle Family System. The protocol is optimized for ESP32-based LoRa devices with limited bandwidth while ensuring message authenticity, confidentiality, and replay protection.

## Cryptographic Foundations

- **Key hierarchy**
  - `K_family`: 256-bit pre-shared root key installed during provisioning.
  - `K_node[i]`: Unique 256-bit key per node derived via HKDF: `HKDF-SHA256(K_family, node_id || salt)`.
  - `K_session`: Ephemeral 256-bit key derived after successful handshake using ECDH (Curve25519) plus HKDF.
- **Algorithms**
  - ECDH with Curve25519 for session key establishment.
  - AES-256-GCM for authenticated encryption of payloads.
  - HMAC-SHA256 for integrity of handshake frames.
  - Xoshiro256** PRNG seeded with hardware RNG for nonces.

## Device Identity

- Each node is assigned a 4-byte `node_id` constant (e.g., `0x4E435C01` for Newcastle).
- Public keys are stored in a read-only provisioning partition.
- Boot firmware validates that both `node_id` and key material are present; otherwise it enters lockdown.

## Handshake Flow

1. **Beacon**: Every 10 minutes each node emits an unauthenticated, short beacon containing `node_id`, firmware version, and a rolling 8-bit counter. Beacons help neighbours maintain routing tables but carry no sensitive data.
2. **Hello**: When a node needs to send a status update, it broadcasts an encrypted HELLO request:
   - Includes a Curve25519 ephemeral public key (`E_pub`), a nonce, and a truncated HMAC over (`node_id`, `E_pub`, nonce) using `K_node[i]`.
3. **Challenge Response**: Receiving nodes verify the HMAC with the stored `K_node[i]`. If valid, they respond with their own `E_pub` and a challenge nonce encrypted under AES-GCM using `K_family`.
4. **Session Derivation**: Both parties compute `K_session` using HKDF over `ECDH(E_pub_local, E_pub_remote)`, the concatenated nonces, and the latest rolling counter values.
5. **Route Update**: Nodes store `K_session` for 2 hours of inactivity or until reset. Routing tables mark the neighbour as authenticated.

## Message Frame Structure

| Field | Size | Description |
| --- | --- | --- |
| Preamble | 2 bytes | `0xCAFE` identifies encrypted frames. |
| Header | 1 byte | Bits: [7:5]=message type, [4:0]=hop limit. |
| Node ID | 4 bytes | Source node identifier. |
| Timestamp | 4 bytes | Unix epoch minutes (UTC) truncated to 32 bits. |
| Session Counter | 4 bytes | Monotonic counter incremented per message, stored in NVS. |
| Payload Length | 1 byte | `0–48` bytes. |
| Ciphertext | variable | AES-GCM encrypted payload (status, commands). |
| Auth Tag | 12 bytes | AES-GCM tag. |

Message types:
- `000`: Heartbeat (`I'm OK`).
- `001`: SOS alert.
- `010`: Acknowledgement.
- `011`: Admin command (reset, firmware update intent).
- `100`: Mesh diagnostic.

## Replay & Spoofing Protection

- Session counters reset only after new handshake.
- Nodes reject frames with timestamps older than 30 minutes or counters ≤ stored value.
- Failed authentication increments a tamper counter; three consecutive failures force 5-minute radio silence to deter brute-force attempts.

## Mesh Relaying Rules

- Hop limit defaults to 5. Each relay decrements the hop count; frames with `hop == 0` are dropped.
- Nodes maintain neighbour signal quality (RSSI/SNR) for route scoring. Prefer strongest path; fallback to alternate if no ack within 15 seconds.
- Relays cache the last 32 frame hashes to avoid duplicate forwarding.

## Time Synchronization

- GPS-equipped nodes (Newcastle HQ, Placerville) act as time anchors, broadcasting authenticated time sync frames every 6 hours.
- Non-GPS nodes accept a time update only if signed by an anchor node and within ±2 minutes of current clock.

## Key Rotation & Revocation

- Monthly manual rotation recommended. Provisioning tool loads new `K_family` and regenerates derived keys.
- If a node is lost, update the revocation list and broadcast an admin command with the revoked `node_id`. Firmware deletes the corresponding route and ignores further frames from that ID.

