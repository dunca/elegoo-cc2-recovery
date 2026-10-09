import os, sys, termios, time, select
dev = sys.argv[1]
fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
a[4] = a[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, a); termios.tcflush(fd, termios.TCIOFLUSH)
ok = 0
for i in range(5):
    msg = f"CC2-loopback-{i}-0123456789\n".encode()
    os.write(fd, msg); time.sleep(0.15)
    got = b""
    while select.select([fd], [], [], 0.2)[0]:
        got += os.read(fd, 4096)
    print(f"sent {msg!r} got {got!r} -> {'OK' if got == msg else 'MISMATCH'}")
    ok += got == msg
os.close(fd); print(f"{ok}/5 passed")
