# Use the tiangolo/nginx-rtmp base image
FROM tiangolo/nginx-rtmp:latest

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy the custom nginx.conf into the container
COPY nginx.conf /etc/nginx/nginx.conf

# Create the /opt/origin directory and copy index.html into it
RUN mkdir -p /opt/origin/dash/stream
COPY index.html /opt/origin/index.html

# run start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Expose the necessary ports
EXPOSE 1935
EXPOSE 80
CMD ["/start.sh"]