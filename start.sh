#!/bin/bash
ffmpeg -i rtmp://localhost/live/stream -c:v libx264 -b:v 2M -c:a aac -b:a 128k -f dash /opt/origin/dash/stream/manifest.mpd 2>&1 | tee /var/log/ffmpeg.log &
nginx -g 'daemon off;'