"""Tests for tools/parse_btsnoop.py."""

from __future__ import annotations

import io
import struct

from tools.parse_btsnoop import (
    _extract_acl_data,
    _extract_att_payload,
    _parse_att_write,
    _print_results,
    _read_file_header,
    _read_record,
    parse_btsnoop,
)

# --- _read_file_header ---


def test_read_file_header_valid():
    """Valid btsnoop header is parsed correctly."""
    header = b"btsnoop\x00" + struct.pack(">II", 1, 1002)
    f = io.BytesIO(header)
    result = _read_file_header(f)
    assert result == (1, 1002)


def test_read_file_header_invalid():
    """Invalid magic bytes return None."""
    f = io.BytesIO(b"not_btsnoop_data")
    result = _read_file_header(f)
    assert result is None


# --- _read_record ---


def _make_record(flags: int, packet: bytes) -> bytes:
    """Build a raw btsnoop record (24-byte header + packet)."""
    orig_len = len(packet)
    incl_len = len(packet)
    drops = 0
    timestamp = 0
    header = struct.pack(">IIIIQ", orig_len, incl_len, flags, drops, timestamp)
    return header + packet


def test_read_record_valid():
    """A well-formed record is returned."""
    packet = b"\x01\x02\x03"
    raw = _make_record(flags=0, packet=packet)
    f = io.BytesIO(raw)
    result = _read_record(f)
    assert result is not None
    incl_len, flags, data = result
    assert incl_len == 3
    assert flags == 0
    assert data == packet


def test_read_record_eof():
    """Empty stream returns None."""
    f = io.BytesIO(b"")
    assert _read_record(f) is None


def test_read_record_truncated_header():
    """Truncated header returns None."""
    f = io.BytesIO(b"\x00" * 10)
    assert _read_record(f) is None


def test_read_record_truncated_packet():
    """Header claims more data than available returns None."""
    # Header says 100 bytes but only 5 available
    header = struct.pack(">IIIIQ", 100, 100, 0, 0, 0)
    f = io.BytesIO(header + b"\x00" * 5)
    assert _read_record(f) is None


# --- _extract_acl_data ---


def test_extract_acl_data_hci_monitor():
    """Datalink 1002 extracts ACL (type 0x02) data."""
    packet = bytes([0x02]) + b"\xaa\xbb"
    result = _extract_acl_data(1002, packet)
    assert result == b"\xaa\xbb"


def test_extract_acl_data_hci_monitor_non_acl():
    """Datalink 1002 with non-ACL type returns None."""
    packet = bytes([0x04]) + b"\xaa\xbb"
    result = _extract_acl_data(1002, packet)
    assert result is None


def test_extract_acl_data_other_datalink():
    """Non-1002 datalink assumes ACL and returns full packet."""
    packet = b"\xaa\xbb\xcc"
    result = _extract_acl_data(999, packet)
    assert result == packet


def test_extract_acl_data_empty_packet():
    """Datalink 1002 with empty packet falls through to default (assumes ACL)."""
    result = _extract_acl_data(1002, b"")
    assert result == b""


# --- _extract_att_payload ---


def _make_att_packet(att_opcode: int, att_data: bytes = b"") -> bytes:
    """Build HCI ACL data containing an ATT payload on CID 0x0004."""
    l2cap_payload = bytes([att_opcode]) + att_data
    l2cap_len = len(l2cap_payload)
    # HCI ACL header (4 bytes): handle(2) + total_len(2)
    acl_total = l2cap_len + 4  # L2CAP header is 4 bytes
    hci_header = struct.pack("<HH", 0x0040, acl_total)
    # L2CAP header: length(2) + CID(2)
    l2cap_header = struct.pack("<HH", l2cap_len, 0x0004)
    return hci_header + l2cap_header + l2cap_payload


def test_extract_att_payload_valid():
    """ATT opcode is extracted from valid packet."""
    hci_data = _make_att_packet(0x12, b"\x01\x00\x41")
    result = _extract_att_payload(hci_data)
    assert result is not None
    opcode, data = result
    assert opcode == 0x12


def test_extract_att_payload_non_att_cid():
    """Non-ATT CID (not 0x0004) returns None."""
    hci_header = struct.pack("<HH", 0x0040, 5)
    l2cap_header = struct.pack("<HH", 1, 0x0005)  # CID != 0x0004
    hci_data = hci_header + l2cap_header + b"\x12"
    result = _extract_att_payload(hci_data)
    assert result is None


def test_extract_att_payload_too_short():
    """Packet shorter than 4 bytes returns None."""
    assert _extract_att_payload(b"\x00\x01\x02") is None


def test_extract_att_payload_short_acl():
    """ACL data too short for L2CAP header returns None."""
    hci_header = struct.pack("<HH", 0x0040, 0)
    assert _extract_att_payload(hci_header) is None


def test_extract_att_payload_empty_l2cap():
    """Empty L2CAP payload returns None."""
    hci_header = struct.pack("<HH", 0x0040, 4)
    l2cap_header = struct.pack("<HH", 0, 0x0004)
    result = _extract_att_payload(hci_header + l2cap_header)
    assert result is None


# --- _parse_att_write ---


def test_parse_att_write_request():
    """ATT Write Request (0x12) is parsed."""
    l2cap_data = bytes([0x12]) + struct.pack("<H", 0x0015) + b"hello"
    result = _parse_att_write(0x12, l2cap_data, flags=0, packet_num=5)
    assert result is not None
    assert result["packet"] == 5
    assert result["direction"] == "SENT"
    assert result["opcode"] == "Write Request"
    assert result["handle"] == 0x0015
    assert result["value"] == "hello"


def test_parse_att_write_command():
    """ATT Write Command (0x52) is parsed."""
    l2cap_data = bytes([0x52]) + struct.pack("<H", 0x000A) + b"test"
    result = _parse_att_write(0x52, l2cap_data, flags=1, packet_num=10)
    assert result is not None
    assert result["direction"] == "RECV"
    assert result["opcode"] == "Write Command"


def test_parse_att_write_non_utf8():
    """Non-UTF-8 values fall back to hex."""
    raw = bytes([0xFF, 0xFE])
    l2cap_data = bytes([0x12]) + struct.pack("<H", 0x0001) + raw
    result = _parse_att_write(0x12, l2cap_data, flags=0, packet_num=1)
    assert result is not None
    assert result["value"] == raw.hex()


def test_parse_att_write_wrong_opcode():
    """Non-write opcodes return None."""
    l2cap_data = bytes([0x0B]) + struct.pack("<H", 0x0001) + b"x"
    assert _parse_att_write(0x0B, l2cap_data, flags=0, packet_num=1) is None


def test_parse_att_write_too_short():
    """Data shorter than 3 bytes returns None."""
    assert _parse_att_write(0x12, b"\x12\x00", flags=0, packet_num=1) is None


# --- _print_results ---


def test_print_results(capsys):
    """Results are printed with correct formatting."""
    writes = [
        {
            "packet": 1,
            "direction": "SENT",
            "opcode": "Write Request",
            "handle": 0x0015,
            "value": "hello",
            "hex": "68656c6c6f",
        }
    ]
    _print_results(10, writes)
    output = capsys.readouterr().out
    assert "Total packets: 10" in output
    assert "ATT Write commands found: 1" in output
    assert "Packet #1 [SENT]" in output
    assert "0x0015" in output
    assert "hello" in output


def test_print_results_hex_differs(capsys):
    """Hex line is printed when value differs from hex."""
    writes = [
        {
            "packet": 1,
            "direction": "SENT",
            "opcode": "Write Request",
            "handle": 0x0001,
            "value": "fffe",
            "hex": "fffe",
        }
    ]
    _print_results(1, writes)
    output = capsys.readouterr().out
    # When value == hex, no extra "Hex:" line
    assert output.count("fffe") == 1


# --- parse_btsnoop integration ---


def _build_btsnoop_file(records: list[tuple[int, bytes]]) -> bytes:
    """Build a minimal btsnoop file with given (flags, packet) records."""
    header = b"btsnoop\x00" + struct.pack(">II", 1, 1002)
    data = header
    for flags, packet in records:
        data += _make_record(flags, packet)
    return data


def test_parse_btsnoop_valid_file(tmp_path, capsys):
    """Full parse of a btsnoop file with one ATT write."""
    # Build an ACL packet with ATT Write Request
    att_payload = struct.pack("<H", 0x0015) + b'[2,{"PowerOn":"ON"}]'
    l2cap_payload = bytes([0x12]) + att_payload
    l2cap_header = struct.pack("<HH", len(l2cap_payload), 0x0004)
    acl_header = struct.pack("<HH", 0x0040, len(l2cap_header) + len(l2cap_payload))
    packet = bytes([0x02]) + acl_header + l2cap_header + l2cap_payload

    filepath = tmp_path / "test.log"
    filepath.write_bytes(_build_btsnoop_file([(0, packet)]))

    parse_btsnoop(filepath)
    output = capsys.readouterr().out
    assert "ATT Write commands found: 1" in output
    assert "PowerOn" in output


def test_parse_btsnoop_invalid_header(tmp_path, capsys):
    """Invalid file header stops parsing."""
    filepath = tmp_path / "bad.log"
    filepath.write_bytes(b"not_a_btsnoop_file_at_all")

    parse_btsnoop(filepath)
    output = capsys.readouterr().out
    assert "Not a valid btsnoop" in output


def test_parse_btsnoop_no_att_writes(tmp_path, capsys):
    """File with non-ATT packets reports zero writes."""
    # Non-ACL packet (HCI type 0x04 = event)
    packet = bytes([0x04]) + b"\x00\x01\x02\x03"
    filepath = tmp_path / "noatt.log"
    filepath.write_bytes(_build_btsnoop_file([(0, packet)]))

    parse_btsnoop(filepath)
    output = capsys.readouterr().out
    assert "ATT Write commands found: 0" in output
