#!/usr/bin/env bash
# Is the launcher progressing (reading new media files) or wedged?
PID=$(pgrep -f launch_pemb3l_flight.py | head -1)
if [ -z "$PID" ]; then
  echo "launcher process: GONE"
else
  echo "launcher pid $PID"
  ps -o pid,etime,pcpu,stat,wchan:24 -p "$PID"
  echo "  io:"
  grep -E "^(read_bytes|rchar)" "/proc/$PID/io" 2>/dev/null | sed 's/^/    /'
  echo "  current file descriptors on /mnt/e (sample):"
  ls -l "/proc/$PID/fd" 2>/dev/null | grep -o '/mnt/e/.*' | head -3 | sed 's/^/    /'
fi
echo
echo "competing /mnt/e scanners:"
pgrep -af "find /mnt/e" || echo "  (none)"
echo
echo "load: $(cat /proc/loadavg)"
