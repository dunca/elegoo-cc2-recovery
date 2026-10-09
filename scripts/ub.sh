#!/bin/zsh
# Send one U-Boot command via the console bridge and wait for the next prompt; print its output.
S="${CC2_KIT:-$(cd "$(dirname "$0")" && pwd)}"
L="${CC2_LOG:-$S/../cc2-boot.log}"
T=${UB_TIMEOUT:-60}
for cmd in "$@"; do
  before=$(stat -f %z $L)
  printf '%s\n' "$cmd" >> $S/uart_inbox.txt
  for i in $(seq 1 $((T*5))); do
    sz=$(stat -f %z $L)
    if [ $sz -gt $before ] && tail -c 4 $L | LC_ALL=C tr -d '\r\n' | grep -q '=> *$'; then break; fi
    sleep 0.2
  done
  tail -c +$((before+1)) $L | LC_ALL=C tr -d '\r' | grep -v '^>>> '
done
