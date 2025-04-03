# DASH Live Stream Demo with ffmpeg

This is a demo/template for live streaming using OBS to stream through RMTP protocol to a server that will then encode using ffmpeg and display the video in real time using DASH protocol

## visit website to see live stream
[Live Demo](http://45.32.211.50/)

# How to build and run

## copy files to VPS server

```
scp -r ./ root@<ip-to-your-server>:~/dash_demo/
```

## build image and run container

```
cd ~/dash_demo
docker build -t dash-demo . && docker run -d -p 1935:1935 -p 80:80 dash-demo
```

## kill container

```
docker ps // get container id
docker kill <container-id>
```