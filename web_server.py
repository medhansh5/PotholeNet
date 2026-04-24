"""
PotholeNet Web Server

Bridges the Python PotholeNet Engine with the JavaScript frontend
Provides REST API endpoints and WebSocket for real-time updates
"""

import asyncio
import websockets
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api import get_api, process_real_time_data
from engine import SensorReading

class PotholeNetAPIHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for PotholeNet API"""
    
    def __init__(self, *args, **kwargs):
        self.api = get_api()
        self.detections_db = []  # In-memory storage for demo
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.serve_file('index.html')
        elif self.path == '/map.js':
            self.serve_file('map.js')
        elif self.path == '/api/potholes':
            self.serve_potholes()
        elif self.path == '/api/stats':
            self.serve_stats()
        else:
            # Try to serve static files
            if os.path.exists(self.path[1:]):
                self.serve_file(self.path[1:])
            else:
                self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/detection':
            self.handle_detection()
        else:
            self.send_error(404)
    
    def serve_file(self, filename):
        """Serve a static file"""
        try:
            with open(filename, 'rb') as f:
                content = f.read()
                
            # Set content type based on file extension
            if filename.endswith('.html'):
                content_type = 'text/html'
            elif filename.endswith('.js'):
                content_type = 'application/javascript'
            elif filename.endswith('.css'):
                content_type = 'text/css'
            else:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            
        except FileNotFoundError:
            self.send_error(404)
    
    def serve_potholes(self):
        """Serve pothole detections as JSON"""
        try:
            # Return stored detections
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(self.detections_db)
            self.wfile.write(response.encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def serve_stats(self):
        """Serve statistics as JSON"""
        try:
            # Calculate statistics
            total = len(self.detections_db)
            recent = len([d for d in self.detections_db 
                         if d['timestamp'] > time.time() - 3600])  # Last hour
            high_severity = len([d for d in self.detections_db 
                               if d['severity'] == 'high'])
            
            avg_confidence = 0
            if self.detections_db:
                avg_confidence = sum(d['confidence'] for d in self.detections_db) / len(self.detections_db)
            
            stats = {
                'total': total,
                'recent': recent,
                'high_severity': high_severity,
                'avg_confidence': avg_confidence * 100
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(stats)
            self.wfile.write(response.encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_detection(self):
        """Handle new detection submission"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            detection_data = json.loads(post_data.decode())
            
            # Validate detection data
            required_fields = ['latitude', 'longitude', 'confidence', 'severity']
            for field in required_fields:
                if field not in detection_data:
                    self.send_error(400, f'Missing field: {field}')
                    return
            
            # Add timestamp if not provided
            if 'timestamp' not in detection_data:
                detection_data['timestamp'] = time.time()
            
            # Store detection
            self.detections_db.append(detection_data)
            
            # Broadcast to WebSocket clients
            if hasattr(self.server, 'websocket_manager'):
                asyncio.run(self.server.websocket_manager.broadcast({
                    'type': 'pothole_detection',
                    'detection': detection_data
                }))
            
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps({'status': 'success', 'id': len(self.detections_db)})
            self.wfile.write(response.encode())
            
        except Exception as e:
            self.send_error(500, str(e))

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.clients = set()
    
    async def register(self, websocket):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        print(f"WebSocket client connected. Total clients: {len(self.clients)}")
        
        try:
            # Send initial data to new client
            await websocket.send(json.dumps({
                'type': 'connection_established',
                'message': 'Connected to PotholeNet real-time updates'
            }))
        except:
            pass
    
    async def unregister(self, websocket):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        print(f"WebSocket client disconnected. Total clients: {len(self.clients)}")
    
    async def broadcast(self, message):
        """Broadcast message to all connected clients"""
        if self.clients:
            message_str = json.dumps(message)
            disconnected = set()
            
            for client in self.clients:
                try:
                    await client.send(message_str)
                except:
                    disconnected.add(client)
            
            # Remove disconnected clients
            self.clients -= disconnected

class PotholeNetWebServer:
    """Main web server combining HTTP and WebSocket"""
    
    def __init__(self, host='localhost', port=8000, ws_port=8765):
        self.host = host
        self.port = port
        self.ws_port = ws_port
        self.websocket_manager = WebSocketManager()
        self.http_server = None
        self.simulation_running = False
    
    def start_http_server(self):
        """Start the HTTP server"""
        handler = PotholeNetAPIHandler
        
        # Patch the handler to include WebSocket manager
        original_init = handler.__init__
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.server.websocket_manager = self.websocket_manager
        
        handler.__init__ = patched_init
        
        self.http_server = HTTPServer((self.host, self.port), handler)
        print(f"HTTP server starting on http://{self.host}:{self.port}")
        self.http_server.serve_forever()
    
    async def start_websocket_server(self):
        """Start the WebSocket server"""
        async def handle_client(websocket, path):
            await self.websocket_manager.register(websocket)
            try:
                async for message in websocket:
                    # Handle incoming messages if needed
                    pass
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                await self.websocket_manager.unregister(websocket)
        
        print(f"WebSocket server starting on ws://{self.host}:{self.ws_port}")
        async with websockets.serve(handle_client, self.host, self.ws_port):
            await asyncio.Future()  # Run forever
    
    def start_simulation(self):
        """Start pothole detection simulation"""
        import random
        import numpy as np
        
        def simulate():
            api = get_api()
            api.clear_buffers()
            
            # Simulate movement along a path
            base_lat, base_lng = 40.7128, -74.0060
            
            for i in range(1000):  # 1000 detections
                timestamp = time.time()
                
                # Simulate sensor data
                x = random.gauss(0, 0.1)
                y = random.gauss(0, 0.1)
                
                # Random pothole events
                if random.random() < 0.1:  # 10% chance
                    z = random.gauss(2.0, 0.5)  # High Z value
                    severity = random.choice(['low', 'medium', 'high'])
                    confidence = random.uniform(0.7, 0.95)
                else:
                    z = random.gauss(0, 0.1)
                    severity = None
                    confidence = None
                
                # Simulate GPS movement
                lat = base_lat + i * 0.0001
                lng = base_lng + i * 0.0001
                
                # Process detection
                api.add_sensor_data(timestamp, x, y, z, lat, lng)
                detections = api.process_and_get_detections()
                
                # If we have a simulated pothole, create detection
                if severity and confidence:
                    detection = {
                        'latitude': lat,
                        'longitude': lng,
                        'confidence': confidence,
                        'severity': severity,
                        'timestamp': timestamp
                    }
                    
                    # Add to HTTP handler's database
                    if self.http_server:
                        for handler in self.http_server.handlers:
                            if hasattr(handler, 'detections_db'):
                                handler.detections_db.append(detection)
                    
                    # Broadcast via WebSocket
                    asyncio.run(self.websocket_manager.broadcast({
                        'type': 'pothole_detection',
                        'detection': detection
                    }))
                
                time.sleep(0.5)  # One detection every 0.5 seconds
        
        simulation_thread = threading.Thread(target=simulate, daemon=True)
        simulation_thread.start()
        print("Pothole detection simulation started")
    
    def run(self):
        """Run both HTTP and WebSocket servers"""
        # Start HTTP server in separate thread
        http_thread = threading.Thread(target=self.start_http_server, daemon=True)
        http_thread.start()
        
        # Start WebSocket server
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Start simulation after a short delay
        threading.Timer(2.0, self.start_simulation).start()
        
        try:
            loop.run_until_complete(self.start_websocket_server())
        except KeyboardInterrupt:
            print("\nShutting down servers...")
            if self.http_server:
                self.http_server.shutdown()

if __name__ == "__main__":
    print("PotholeNet Web Server")
    print("====================")
    print("Starting web interface for PotholeNet Engine...")
    print("Open http://localhost:8000 in your browser")
    print()
    
    server = PotholeNetWebServer()
    server.run()
