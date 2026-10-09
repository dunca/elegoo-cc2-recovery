#!/usr/bin/env python3
"""Stage the files for "SSH via U-Boot ext4write" and write the RAM-slot manifest.

Nothing from Elegoo is shipped with this repo. Extract the official v01.03.02.51 rootfs yourself
(verify its RSA signature first; see the README), then point this script at it.

usage: make_stage.py ROOTFS_DIR PUBLIC_KEY OUT_DIR
  ROOTFS_DIR  unsquashfs'd official v01 rootfs (must contain usr/sbin/sshd etc.)
  PUBLIC_KEY  your SSH public key (e.g. ~/.ssh/id_ed25519.pub)
  OUT_DIR     staging directory to create (keep it out of git: it holds private host keys)

Writes OUT_DIR/stage/<files> and OUT_DIR/manifest.tsv (name, RAM address, size, CRC32).
Each file gets a 1 MiB slot from 0x40000000; rc.local (installer) is placed last.
"""
import hashlib, os, shutil, subprocess, sys, zlib

EXPECTED_SHA256 = {  # official v01.03.02.51 rootfs
    "usr/sbin/sshd": "7746b7085a1539f0a8db1aea89a97ea0ed7e8e5e722fecd476fdedfa1e7a002c",
    "usr/lib/sftp-server": "00bc6699d50235c6e95b2a9f4f71ea082ab4b41d3d5c8c98a6fbfe31fe461238",
    "etc/init.d/sshd": "69b42d5f0adf20eeffd5218bc9e955af1d3590d68a07c21ad90128ea7a6930d8",
    "etc/ssh/sshd_config": "3204a74a8986ebf71d93818f264a88a92e3dc3f691afa57afd032175c1b10e81",
    "lib/upgrade/keep.d/openssh-server": "4af6a8ae9675582d20ba08d8af0f179d548a8219257b77af17fdeb82487b61f8",
}
STAGE_NAMES = {
    "usr/sbin/sshd": "cc2ssh-sshd",
    "usr/lib/sftp-server": "cc2ssh-sftp-server",
    "etc/init.d/sshd": "cc2ssh-sshd.init",
    "etc/ssh/sshd_config": "cc2ssh-sshd_config",
    "lib/upgrade/keep.d/openssh-server": "cc2ssh-keep",
}

def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    rootfs, pubkey, out = sys.argv[1:4]
    here = os.path.dirname(os.path.abspath(__file__))
    stage = os.path.join(out, "stage")
    os.makedirs(stage, exist_ok=True)

    for rel, name in STAGE_NAMES.items():
        src = os.path.join(rootfs, rel)
        digest = hashlib.sha256(open(src, "rb").read()).hexdigest()
        if digest != EXPECTED_SHA256[rel]:
            sys.exit(f"{rel}: SHA-256 {digest} does not match the official v01.03.02.51 file")
        shutil.copyfile(src, os.path.join(stage, name))
    shutil.copyfile(pubkey, os.path.join(stage, "cc2ssh-authorized_keys"))
    for t in ("rsa", "ecdsa", "ed25519"):
        key = os.path.join(stage, f"cc2ssh-host_{t}_key")
        if not os.path.exists(key):
            subprocess.run(["ssh-keygen", "-q", "-t", t, "-N", "", "-C", f"cc2-host-{t}", "-f", key], check=True)
    shutil.copyfile(os.path.join(here, "rc.local"), os.path.join(stage, "rc.local"))

    names = sorted(os.listdir(stage), key=lambda n: (n == "rc.local", n))
    rows = []
    for i, n in enumerate(names):
        data = open(os.path.join(stage, n), "rb").read()
        if len(data) >= 0x100000:
            sys.exit(f"{n} is larger than its 1 MiB RAM slot")
        rows.append(f"{n}\t0x{0x40000000 + i * 0x100000:08x}\t0x{len(data):x}\t{zlib.crc32(data) & 0xffffffff:08x}")
    open(os.path.join(out, "manifest.tsv"), "w").write("\n".join(rows) + "\n")
    print("\n".join(rows))

if __name__ == "__main__":
    main()
