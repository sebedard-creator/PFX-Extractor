"""Small synthetic native-profile BWF fixtures; no production recordings."""
import hashlib
import struct
import numpy as np


def wave_bytes(n=48000, tc=172800000, level=.02, identity='default'):
    def chunk(tag, data):
        return tag + struct.pack('<I', len(data)) + data + b'\0' * (len(data) % 2)
    bext = bytearray(602)
    struct.pack_into('<Q', bext, 338, tc)
    struct.pack_into('<H', bext, 346, 1)
    bext[348:380] = bytes.fromhex('060a2b340101010501010f1013000000') + hashlib.sha256(identity.encode()).digest()[:16]
    fmt = struct.pack('<HHIIHHHHI', 0xfffe, 1, 48000, 192000, 4, 32, 22, 32, 4)
    fmt += bytes.fromhex('0300000000001000800000aa00389b71')
    body = b'WAVE' + chunk(b'fmt ', fmt) + chunk(b'bext', bext) + chunk(b'fact', struct.pack('<I', n))
    body += chunk(b'data', np.full(n, level, np.float32).tobytes())
    return b'RIFF' + struct.pack('<I', len(body)) + body
