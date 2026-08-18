#!/usr/bin/env bash
# Is the path-safety rule merely a regex, or also a filesystem constraint?
# Slices land under data_root (/mnt/e = NTFS via DrvFs). Colons are illegal in
# NTFS filenames. Test both filesystems, then clean up. Touches no project data.
NAME='slurp:devel:005518:audio-1490203960'

for base in /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/tmp-pathsafety-probe \
            /home/chao/tmp-pathsafety-probe; do
  echo "=== base: $base ==="
  mkdir -p "$base" 2>&1
  if mkdir -p "$base/$NAME" 2>&1; then
    if echo test > "$base/$NAME/i0000.wav" 2>&1; then
      echo "RESULT: colon directory + file CREATED ok"
      ls -la "$base/$NAME" 2>&1
    else
      echo "RESULT: directory made but FILE WRITE REFUSED"
    fi
  else
    echo "RESULT: mkdir REFUSED"
  fi
  rm -rf "$base" 2>&1
  echo "cleaned: $(test -e "$base" && echo STILL-PRESENT || echo gone)"
  echo
done
