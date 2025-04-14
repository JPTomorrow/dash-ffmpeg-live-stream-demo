#!/bin/bash
echo "cwd: $(pwd)"
python process_stream.py ./stream root@45.32.211.50:~/stream &
ffmpeg -re -fflags +genpts -i obs-recordings/recording.ts -c:v libx264 -b:v 1500k -c:a aac -b:a 128k -f dash -window_size 5 -extra_window_size 10 -remove_at_exit 0 -seg_duration 4 ./stream/output.mpd