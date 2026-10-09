#!/usr/bin/env python3
"""Rebuild the two CC2 U-Boot env copies from `md.b` dumps and save a verified backup.

usage: env_backup.py dump_copy1.txt dump_copy2.txt OUTDIR
Dumps come from `md.b 0x40000000 0x2000` and `md.b 0x40100000 0x2000` after
`mmc read 0x40000000 0xb1f8 0x100` / `mmc read 0x40100000 0xb3f0 0x100`.
"""
import os, re, struct, sys, zlib

ENV_SIZE, DUMP = 0x20000, 0x2000
copies = [(sys.argv[1], 0x40000000, "env-copy1-p3-env.bin"),
          (sys.argv[2], 0x40100000, "env-copy2-p4-env-redund.bin")]
out = sys.argv[3]
os.makedirs(out, exist_ok=True)
ok = True
for path, base, name in copies:
    buf = bytearray(DUMP)
    for line in open(path, errors="replace"):
        m = re.match(r"^([0-9a-f]{8}): ((?:[0-9a-f]{2} ){16})", line.strip())
        if m and 0 <= int(m.group(1), 16) - base < DUMP:
            a = int(m.group(1), 16) - base
            buf[a:a + 16] = bytes(int(x, 16) for x in m.group(2).split())
    img = bytes(buf) + b"\0" * (ENV_SIZE - DUMP)
    stored, calc = struct.unpack("<I", img[:4])[0], zlib.crc32(img[5:]) & 0xFFFFFFFF
    match = stored == calc
    ok &= match
    print(f"{name}: flags=0x{img[4]:02x} crc stored={stored:08x} calc={calc:08x} {'MATCH' if match else 'MISMATCH'}")
    open(os.path.join(out, name), "wb").write(img)
    env = [kv.decode(errors="replace") for kv in img[5:].split(b"\0\0")[0].split(b"\0") if kv]
    open(os.path.join(out, name.replace(".bin", ".txt")), "w").write("\n".join(env) + "\n")
    for kv in env:
        if kv.split("=")[0] in ("boot_partition", "root_partition", "systemAB_next"):
            print("   ", kv)
sys.exit(0 if ok else 1)
