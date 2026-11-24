"""Bygger en liten Modbus/TCP-PCAP uten eksterne avhengigheter.

Kun syntetiske adresser fra dokumentasjonsområdet (192.0.2.0/24, RFC 5737).
"""
import random
import socket
import struct

CLIENT = ("192.0.2.10", 49152)
SERVER = ("192.0.2.20", 502)
CLIENT_MAC = bytes.fromhex("020000000010")
SERVER_MAC = bytes.fromhex("020000000020")


def _csum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\0"
    s = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


class Flow:
    def __init__(self):
        self.packets: list[tuple[float, bytes]] = []
        self.t = 1_700_000_000.0
        self.seq = {"c": 1000, "s": 5000}
        self.ip_id = 1

    def _send(self, side: str, flags: int, payload: bytes = b""):
        (src, sp), (dst, dp) = (CLIENT, SERVER) if side == "c" else (SERVER, CLIENT)
        smac, dmac = (CLIENT_MAC, SERVER_MAC) if side == "c" else (SERVER_MAC, CLIENT_MAC)
        other = "s" if side == "c" else "c"
        ack = self.seq[other] if flags & 0x10 else 0
        tcp = struct.pack("!HHIIBBHHH", sp, dp, self.seq[side], ack, 5 << 4, flags, 65535, 0, 0)
        sip, dip = socket.inet_aton(src), socket.inet_aton(dst)
        pseudo = sip + dip + struct.pack("!BBH", 0, 6, len(tcp) + len(payload))
        tcp = tcp[:16] + struct.pack("!H", _csum(pseudo + tcp + payload)) + tcp[18:]
        ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp) + len(payload),
                         self.ip_id, 0x4000, 64, 6, 0, sip, dip)
        ip = ip[:10] + struct.pack("!H", _csum(ip)) + ip[12:]
        self.ip_id += 1
        self.t += 0.004
        self.packets.append((self.t, dmac + smac + b"\x08\x00" + ip + tcp + payload))
        self.seq[side] += len(payload) + (1 if flags & 0x02 else 0)

    def handshake(self):
        self._send("c", 0x02)
        self._send("s", 0x12)
        self._send("c", 0x10)

    def exchange(self, request_pdu: bytes, response_pdu: bytes, tid: int, unit: int = 1):
        self._send("c", 0x18, _adu(tid, unit, request_pdu))
        self._send("s", 0x18, _adu(tid, unit, response_pdu))
        self.t += 0.2


def _adu(tid: int, unit: int, pdu: bytes) -> bytes:
    return struct.pack("!HHHB", tid, 0, len(pdu) + 1, unit) + pdu


def _regs(values):
    return b"".join(struct.pack("!H", v) for v in values)


def build_modbus_pcap(path, flag: str, rng: random.Random) -> None:
    data = flag.encode("ascii")
    if len(data) % 2:
        data += b"\0"
    nregs = len(data) // 2
    flag_addr = rng.randint(100, 200)
    coil = rng.randint(0, 63)

    steps = []  # (request_pdu, response_pdu)
    for _ in range(rng.randint(3, 5)):
        vals = [rng.randint(0, 5000) for _ in range(4)]
        steps.append((struct.pack("!BHH", 3, 0, 4), struct.pack("!BB", 3, 8) + _regs(vals)))
    for _ in range(2):
        steps.append((struct.pack("!BHH", 1, 0, 8), struct.pack("!BBB", 1, 1, rng.randint(0, 255))))
    steps.append((struct.pack("!BHH", 5, coil, 0xFF00), struct.pack("!BHH", 5, coil, 0xFF00)))
    reg = rng.randint(10, 50)
    val = rng.randint(1, 3000)
    steps.append((struct.pack("!BHH", 6, reg, val), struct.pack("!BHH", 6, reg, val)))
    flag_step = (
        struct.pack("!BHHB", 16, flag_addr, nregs, nregs * 2) + data,
        struct.pack("!BHH", 16, flag_addr, nregs),
    )
    rng.shuffle(steps)
    steps.insert(rng.randint(len(steps) // 2, len(steps)), flag_step)

    flow = Flow()
    flow.handshake()
    for i, (req, resp) in enumerate(steps, start=1):
        flow.exchange(req, resp, tid=i)

    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for t, frame in flow.packets:
            sec = int(t)
            f.write(struct.pack("<IIII", sec, int((t - sec) * 1_000_000), len(frame), len(frame)))
            f.write(frame)
