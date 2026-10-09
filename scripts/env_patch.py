#!/usr/bin/env python3
"""Generate the U-Boot `mw` commands that switch a CC2 to the other A/B slot.

usage: env_patch.py BACKUP_DIR OUT_CMDS_FILE [A|B]
Reads the verified backups from env_backup.py, flips boot_partition, root_partition and
systemAB_next to the target slot (default: the one not currently selected), recomputes
each copy's CRC, writes *.PATCHED.bin next to the backups and the command list to OUT.
Every edit is one byte, so no offsets shift.
"""
import os, struct, sys, zlib

d, out = sys.argv[1], sys.argv[2]
copies = [("env-copy1-p3-env.bin", 0x40000000), ("env-copy2-p4-env-redund.bin", 0x40100000)]
first = open(os.path.join(d, copies[0][0]), "rb").read()
cur = "A" if b"\0systemAB_next=A\0" in first else "B"
dst = sys.argv[3] if len(sys.argv) > 3 else ("B" if cur == "A" else "A")
if dst == cur:
    sys.exit(f"already on slot {cur}")
edits = [(f"\0boot_partition=boot{cur}\0", f"\0boot_partition=boot{dst}\0"),
         (f"\0root_partition=rootfs{cur}\0", f"\0root_partition=rootfs{dst}\0"),
         (f"\0systemAB_next={cur}\0", f"\0systemAB_next={dst}\0")]
cmds = []
for name, base in copies:
    img = bytearray(open(os.path.join(d, name), "rb").read())
    for old, new in edits:
        old, new = old.encode(), new.encode()
        assert img.count(old) == 1, f"{name}: expected exactly one {old!r}"
        off = img.find(old)
        for i, (a, b) in enumerate(zip(old, new)):
            if a != b:
                cmds.append(f"mw.b 0x{base + off + i:08x} 0x{b:02x}")
                img[off + i] = b
    crc = zlib.crc32(bytes(img[5:])) & 0xFFFFFFFF
    img[0:4] = struct.pack("<I", crc)
    cmds.append(f"mw.l 0x{base:08x} 0x{crc:08x}")
    open(os.path.join(d, name.replace(".bin", ".PATCHED.bin")), "wb").write(img)
    print(f"{name}: {cur} -> {dst}, flags=0x{img[4]:02x} (unchanged), new crc={crc:08x}")
open(out, "w").write("\n".join(cmds) + "\n")
print("\n".join(cmds))
