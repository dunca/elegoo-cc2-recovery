#!/bin/sh
# CC2 memory logger: one CSV line per minute to /opt/usr/memlog/memlog.csv (disk, not RAM).
# Self-cleaning: past 2 MB (~1 week) the log becomes memlog.prev.csv; disk use stays under ~4 MB.
D=/opt/usr/memlog; F=$D/memlog.csv; MAX=2097152; mkdir -p $D
HDR="epoch,uptime_s,mem_avail_kb,mem_free_kb,cached_kb,printer_rss_kb,camera_rss_kb,gui_rss_kb,camera_pid,load1,oom_events"
rss() { p=$(pidof "$1" | cut -d' ' -f1); if [ -n "$p" ]; then awk '/^VmRSS:/{print $2}' /proc/$p/status 2>/dev/null; else echo 0; fi; }
while :; do
  [ -f $F ] && [ $(wc -c < $F) -gt $MAX ] && mv -f $F $D/memlog.prev.csv
  [ -f $F ] || echo "$HDR" > $F
  set -- $(awk '/^MemAvailable:/{a=$2} /^MemFree:/{f=$2} /^Cached:/{c=$2} END{print a, f, c}' /proc/meminfo)
  echo "$(date +%s),$(cut -d. -f1 /proc/uptime),$1,$2,$3,$(rss elegoo_printer),$(rss ai_camera),$(rss ec-eeb001-gui),$(pidof ai_camera | cut -d' ' -f1),$(cut -d' ' -f1 /proc/loadavg),$(dmesg | grep -c -i -E 'out of memory|oom-kill')" >> $F
  sleep 60
done
