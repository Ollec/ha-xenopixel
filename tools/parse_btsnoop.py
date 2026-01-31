#!/usr/bin/env python3
"""Parse btsnoop_hci.log to extract ATT Write commands.

Usage:
    uv run python tools/parse_btsnoop.py references/btsnoop_hci.log
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Any


def _read_file_header(f: Any) -> tuple[int, int] | None:
    """Read and validate the btsnoop file header.

    Returns (version, datalink) or None if invalid.
    """
    header = f.read(16)
    if header[:8] != b"btsnoop\x00":
        print("Not a valid btsnoop file")
        return None

    version = struct.unpack(">I", header[8:12])[0]
    datalink = struct.unpack(">I", header[12:16])[0]
    return version, datalink


def _read_record(f: Any) -> tuple[int, int, bytes] | None:
    """Read a single btsnoop record.

    Returns (incl_len, flags, packet_data) or None if EOF.
    """
    record_header = f.read(24)
    if len(record_header) < 24:
        return None

    _, incl_len, flags, _, _ = struct.unpack(">IIIIQ", record_header)

    packet = f.read(incl_len)
    if len(packet) < incl_len:
        return None

    return incl_len, flags, packet


def _extract_att_payload(hci_data: bytes) -> tuple[int, bytes] | None:
    """Extract ATT opcode and L2CAP payload from HCI ACL data.

    Returns (att_opcode, l2cap_data) or None if not an ATT packet.
    """
    if len(hci_data) < 4:
        return None

    acl_data = hci_data[4:]

    if len(acl_data) < 4:
        return None

    l2cap_cid = struct.unpack("<H", acl_data[2:4])[0]
    l2cap_data = acl_data[4:]

    # ATT is on CID 0x0004
    if l2cap_cid != 0x0004 or len(l2cap_data) < 1:
        return None

    return l2cap_data[0], l2cap_data


def _parse_att_write(
    att_opcode: int, l2cap_data: bytes, flags: int, packet_num: int
) -> dict[str, Any] | None:
    """Parse an ATT Write Request/Command into a result dict."""
    # ATT Write Request (0x12) or ATT Write Command (0x52)
    if att_opcode not in (0x12, 0x52):
        return None
    if len(l2cap_data) < 3:
        return None

    att_handle = struct.unpack("<H", l2cap_data[1:3])[0]
    att_value = l2cap_data[3:]

    direction = "RECV" if (flags & 1) else "SENT"

    try:
        text = att_value.decode("utf-8")
    except UnicodeDecodeError:
        text = att_value.hex()

    opcode_name = "Write Request" if att_opcode == 0x12 else "Write Command"

    return {
        "packet": packet_num,
        "direction": direction,
        "opcode": opcode_name,
        "handle": att_handle,
        "value": text,
        "hex": att_value.hex(),
    }


def _print_results(packet_num: int, att_writes: list[dict[str, Any]]) -> None:
    """Print the parsed ATT write results."""
    print(f"\nTotal packets: {packet_num}")
    print(f"ATT Write commands found: {len(att_writes)}")
    print("=" * 60)

    for w in att_writes:
        print(f"\nPacket #{w['packet']} [{w['direction']}]")
        print(f"  {w['opcode']} to handle 0x{w['handle']:04X}")
        print(f"  Value: {w['value']}")
        if w["value"] != w["hex"]:
            print(f"  Hex: {w['hex']}")


def _extract_acl_data(datalink: int, packet: bytes) -> bytes | None:
    """Extract ACL HCI data from a packet, returning None if not ACL."""
    if datalink == 1002 and len(packet) > 0:
        hci_type = packet[0]
        hci_data = packet[1:]
    else:
        hci_type = 0x02  # Assume ACL
        hci_data = packet

    return hci_data if hci_type == 0x02 else None


def parse_btsnoop(filepath: Path) -> None:
    """Parse btsnoop file and extract ATT writes."""
    with open(filepath, "rb") as f:
        result = _read_file_header(f)
        if result is None:
            return

        version, datalink = result
        print(f"btsnoop version: {version}, datalink: {datalink}")
        print("=" * 60)

        packet_num = 0
        att_writes: list[dict[str, Any]] = []

        while True:
            record = _read_record(f)
            if record is None:
                break

            _, flags, packet = record
            packet_num += 1

            hci_data = _extract_acl_data(datalink, packet)
            if hci_data is None:
                continue

            att_result = _extract_att_payload(hci_data)
            if att_result is None:
                continue

            att_opcode, l2cap_data = att_result
            write = _parse_att_write(att_opcode, l2cap_data, flags, packet_num)
            if write is not None:
                att_writes.append(write)

        _print_results(packet_num, att_writes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_btsnoop.py <btsnoop_hci.log>")
        sys.exit(1)

    parse_btsnoop(Path(sys.argv[1]))
