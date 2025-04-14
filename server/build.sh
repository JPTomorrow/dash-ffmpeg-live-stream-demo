#!/bin/bash
docker build -t dash-demo . && docker run -v ~/stream:/opt/origin/dash/stream -d -p 1935:1935 -p 80:80 dash-demo