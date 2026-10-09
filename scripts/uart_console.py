# Keeps the UART open: logs all output, sends lines appended to an inbox file,
# and optionally spams a key until a U-Boot prompt appears.
import os, sys, termios, time, select, errno
dev, log, inbox, spam, secs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0; a[4] = a[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, a)
open(inbox, "a").close(); pos = os.path.getsize(inbox)
end = time.time() + secs; tail = b""; spamming = bool(spam)
with open(log, "ab", buffering=0) as f:
    f.write(f"\n=== console {time.strftime('%H:%M:%S')} spam={spam!r} ===\n".encode())
    while time.time() < end:
        if spamming:
            try: os.write(fd, spam.encode())
            except OSError: pass
        r = select.select([fd], [], [], 0.02 if spamming else 0.1)[0]
        if r:
            try: d = os.read(fd, 4096)
            except OSError as e:
                if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK): d = b""
                else: raise
            if d:
                f.write(d); tail = (tail + d)[-200:]
                if spamming and b"=>" in tail:
                    spamming = False; f.write(b"\n=== PROMPT, spam stopped ===\n")
        sz = os.path.getsize(inbox)
        if sz > pos:
            with open(inbox, "rb") as ib:
                ib.seek(pos); new = ib.read(); pos = sz
            for line in new.splitlines():
                f.write(b"\n>>> " + line + b"\n")
                for ch in line + b"\r":
                    os.write(fd, bytes([ch])); time.sleep(0.003)
                time.sleep(0.05)
