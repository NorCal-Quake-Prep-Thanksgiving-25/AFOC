#!/usr/bin/env python3
"""Provision TTGO T-Beam nodes with cryptographic material."""

import argparse
import secrets
import struct
import time

import serial

CMD_WRITE_FAMILY = b"FAM"
CMD_WRITE_NODE = b"NOD"
CMD_WRITE_NODE_ID = b"ID\0"
CMD_COMMIT = b"COM"
ACK = b"OK\n"

DEFAULT_BAUD = 115200


def open_port(port: str, baud: int) -> serial.Serial:
    try:
        return serial.Serial(port, baudrate=baud, timeout=2)
    except serial.SerialException as exc:
        raise SystemExit(f"Failed to open serial port {port}: {exc}")


def write_blob(port: serial.Serial, command: bytes, blob: bytes) -> None:
    header = command + struct.pack("<H", len(blob))
    port.write(header + blob)
    port.flush()
    ack = port.read(len(ACK))
    if ack != ACK:
        raise SystemExit(f"Device rejected command {command!r}, received {ack!r}")


def derive_node_key(family_key: bytes, node_id: int) -> bytes:
    salt = node_id.to_bytes(4, "little") + b"NewcastleMeshv1"
    import hashlib
    import hmac

    prk = hmac.new(family_key, salt, hashlib.sha256).digest()
    okm = hmac.new(prk, b"node", hashlib.sha256).digest()
    return okm


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a family mesh node")
    parser.add_argument("port", help="Serial port (e.g. /dev/ttyUSB0)")
    parser.add_argument("--node-id", required=True, type=lambda x: int(x, 0),
                        help="Unique 32-bit node ID (hex or int)")
    parser.add_argument("--family-key", help="Hex-encoded 32-byte family key")
    parser.add_argument("--node-key", help="Hex-encoded 32-byte node key (optional)")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    args = parser.parse_args()

    if args.family_key:
        family_key = bytes.fromhex(args.family_key)
        if len(family_key) != 32:
            raise SystemExit("Family key must be 32 bytes (64 hex chars)")
    else:
        family_key = secrets.token_bytes(32)
        print("Generated random family key:", family_key.hex())

    if args.node_key:
        node_key = bytes.fromhex(args.node_key)
        if len(node_key) != 32:
            raise SystemExit("Node key must be 32 bytes (64 hex chars)")
    else:
        node_key = derive_node_key(family_key, args.node_id)
        print("Derived node key:", node_key.hex())

    with open_port(args.port, args.baud) as port:
        print("Writing family key...")
        write_blob(port, CMD_WRITE_FAMILY, family_key)
        time.sleep(0.1)
        print("Writing node key...")
        write_blob(port, CMD_WRITE_NODE, node_key)
        time.sleep(0.1)
        print("Writing node ID...")
        write_blob(port, CMD_WRITE_NODE_ID, struct.pack("<I", args.node_id))
        time.sleep(0.1)
        print("Committing...")
        write_blob(port, CMD_COMMIT, b"")
    print("Provisioning complete.")


if __name__ == "__main__":
    main()

