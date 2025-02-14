Basic RTSP server for the TOPDON TC100 thermal camera.

Running:
sudo apt-get update
sudo apt-get install -y ffmpeg
sudo apt-get install -y python3-gst-1.0 gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav python3-gi python3-gi-cairo gir1.2-gstreamer-1.0 gir1.2-gst-rtsp-server-1.0
pip3 install python-vlc vlc

python3 thermal_camera.py --headless
