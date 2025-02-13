#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Modified version of Les Wright's Thermal Camera script with HTTP streaming
'''

import cv2
import numpy as np
import argparse
import time
import io
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from socketserver import ThreadingMixIn

class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write('''
                <html>
                <head>
                    <title>Thermal Camera Stream</title>
                </head>
                <body>
                    <h1>Thermal Camera Stream</h1>
                    <img src="/stream" />
                </body>
                </html>
            '''.encode())
        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    frame = self.server.get_frame()
                    if frame is not None:
                        _, jpeg = cv2.imencode('.jpg', frame)
                        self.wfile.write(b'--frame\r\n')
                        self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                        self.wfile.write(jpeg.tobytes())
                        self.wfile.write(b'\r\n')
            except Exception as e:
                print(f"Streaming error: {e}")
        else:
            self.send_error(404)
            self.end_headers()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.current_frame = None

    def set_frame(self, frame):
        self.current_frame = frame

    def get_frame(self):
        return self.current_frame

def is_raspberrypi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False

# Command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--device", type=int, default=0, help="Video Device number e.g. 0")
parser.add_argument("--port", type=int, default=8000, help="HTTP server port")
parser.add_argument("--headless", action="store_true", help="Run in headless mode")
args = parser.parse_args()

# Initialize HTTP server
server = ThreadedHTTPServer(('0.0.0.0', args.port), StreamingHandler)
print(f"Server started at http://[IP_ADDRESS]:{args.port}")

# Start server in a separate thread
server_thread = threading.Thread(target=server.serve_forever)
server_thread.daemon = True
server_thread.start()

# Initialize video capture
isPi = is_raspberrypi()
cap = cv2.VideoCapture('/dev/video'+str(args.device), cv2.CAP_V4L)
if isPi:
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0.0)
else:
    cap.set(cv2.CAP_PROP_CONVERT_RGB, False)

# Settings
width = 256
height = 192
scale = 3
newWidth = width*scale 
newHeight = height*scale
alpha = 1.0
colormap = 0
rad = 0
threshold = 2

print("Press Ctrl+C to stop")

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Split and process frame
        imdata, thdata = np.array_split(frame, 2)
        
        # Process temperature
        hi = thdata[96][128][0]
        lo = thdata[96][128][1]
        lo = lo*256
        rawtemp = hi+lo
        temp = (rawtemp/64)-273.15
        
        # Convert to visible image
        bgr = cv2.cvtColor(imdata, cv2.COLOR_YUV2BGR_YUYV)
        bgr = cv2.convertScaleAbs(bgr, alpha=alpha)
        bgr = cv2.resize(bgr, (newWidth,newHeight), interpolation=cv2.INTER_CUBIC)
        if rad > 0:
            bgr = cv2.blur(bgr, (rad,rad))
            
        # Apply colormap
        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_JET)
        
        # Add temperature overlay
        cv2.putText(heatmap, f"{temp:.1f}C", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Update server frame
        server.set_frame(heatmap)
            
        # Display if not headless
        if not args.headless:
            cv2.imshow('Thermal', heatmap)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

except KeyboardInterrupt:
    print("\nStopping capture...")

finally:
    cap.release()
    server.shutdown()
    server.server_close()
    if not args.headless:
        cv2.destroyAllWindows()
    print("Capture ended")