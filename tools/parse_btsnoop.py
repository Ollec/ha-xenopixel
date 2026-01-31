#!/usr/bin/env python3
"""Parse btsnoop_hci.log to extract ATT Write commands.

Usage:
    uv run python tools/parse_btsnoop.py references/btsnoop_hci.log
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def parse_btsnoop(filepath: Path) -> None:
    """Parse btsnoop file and extract ATT writes."""
    with open(filepath, "rb") as f:
        # Read file header (16 bytes)
        header = f.read(16)
        if header[:8] != b"btsnoop\x00":
            print("Not a valid btsnoop file")
            return

        version = struct.unpack(">I", header[8:12])[0]
        datalink = struct.unpack(">I", header[12:16])[0]
        print(f"btsnoop version: {version}, datalink: {datalink}")
        print("=" * 60)

        packet_num = 0
        att_writes = []

        while True:
            # Read record header (24 bytes)
            record_header = f.read(24)
            if len(record_header) < 24:
                break

            orig_len, incl_len, flags, drops, timestamp = struct.unpack(
                ">IIIIQ", record_header
            )

            # Read packet data
            packet = f.read(incl_len)
            if len(packet) < incl_len:
                break

            packet_num += 1

            # For H4 format (datalink 1002), first byte is HCI type
            # 0x01 = Command, 0x02 = ACL, 0x03 = SCO, 0x04 = Event
            if datalink == 1002 and len(packet) > 0:
                hci_type = packet[0]
                hci_data = packet[1:]
            else:
                hci_type = 0x02  # Assume ACL
                hci_data = packet

            # Only process ACL data (0x02)
            if hci_type != 0x02:
                continue

            # ACL header: handle (2 bytes, includes flags), length (2 bytes)
            if len(hci_data) < 4:
                continue

            acl_handle = struct.unpack("<H", hci_data[0:2])[0] & 0x0FFF
            acl_len = struct.unpack("<H", hci_data[2:4])[0]
            acl_data = hci_data[4:]

            # L2CAP header: length (2 bytes), CID (2 bytes)
            if len(acl_data) < 4:
                continue

            l2cap_len = struct.unpack("<H", acl_data[0:2])[0]
            l2cap_cid = struct.unpack("<H", acl_data[2:4])[0]
            l2cap_data = acl_data[4:]

            # ATT is on CID 0x0004
            if l2cap_cid != 0x0004:
                continue

            if len(l2cap_data) < 1:
                continue

            att_opcode = l2cap_data[0]

            # ATT Write Request (0x12) or ATT Write Command (0x52)
            if att_opcode in (0x12, 0x52):
                if len(l2cap_data) >= 3:
                    att_handle = struct.unpack("<H", l2cap_data[1:3])[0]
                    att_value = l2cap_data[3:]

                    # Determine direction from flags
                    # Bit 0: 0 = sent, 1 = received
                    direction = "RECV" if (flags & 1) else "SENT"

                    # Try to decode as UTF-8
                    try:
                        text = att_value.decode("utf-8")
                    except UnicodeDecodeError:
                        text = att_value.hex()

                    opcode_name = (
                        "Write Request" if att_opcode == 0x12 else "Write Command"
                    )

                    att_writes.append(
                        {
                            "packet": packet_num,
                            "direction": direction,
                            "opcode": opcode_name,
                            "handle": att_handle,
                            "value": text,
                            "hex": att_value.hex(),
                        }
                    )

        print(f"\nTotal packets: {packet_num}")
        print(f"ATT Write commands found: {len(att_writes)}")
        print("=" * 60)

        for w in att_writes:
            print(f"\nPacket #{w['packet']} [{w['direction']}]")
            print(f"  {w['opcode']} to handle 0x{w['handle']:04X}")
            print(f"  Value: {w['value']}")
            if w["value"] != w["hex"]:
                print(f"  Hex: {w['hex']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_btsnoop.py <btsnoop_hci.log>")
        sys.exit(1)

    parse_btsnoop(Path(sys.argv[1]))
