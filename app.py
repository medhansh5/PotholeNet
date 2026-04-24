"""
PotholeNet Flask Application

Web application for real-time pothole detection and mapping
Integrates with PotholeNet Engine for signal processing and classification
"""

from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import json
import time
from datetime import datetime, timedelta
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api import get_api, process_real_time_data
from engine import SensorReading

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///potholes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Database model for pothole detections
class PotholeDetection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    severity = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'confidence': self.confidence,
            'severity': self.severity,
            'timestamp': self.timestamp,
            'created_at': self.created_at.isoformat()
        }

# Initialize API
pothole_api = get_api()

def init_database():
    """Initialize the database with tables"""
    with app.app_context():
        db.create_all()
        print("Database initialized successfully")

@app.route('/')
def index():
    """Serve the main map page"""
    return render_template('index.html')

@app.route('/api/potholes')
def get_potholes():
    """
    Return JSON list of all pothole coordinates from database
    Endpoint for map.js auto-refresh functionality
    """
    try:
        # Get all pothole detections from database
        detections = PotholeDetection.query.order_by(PotholeDetection.created_at.desc()).all()
        
        # Convert to JSON format
        potholes = [detection.to_dict() for detection in detections]
        
        return jsonify({
            'status': 'success',
            'count': len(potholes),
            'potholes': potholes,
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/potholes/recent')
def get_recent_potholes():
    """Get potholes from the last hour"""
    try:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        detections = PotholeDetection.query.filter(
            PotholeDetection.created_at >= one_hour_ago
        ).order_by(PotholeDetection.created_at.desc()).all()
        
        potholes = [detection.to_dict() for detection in detections]
        
        return jsonify({
            'status': 'success',
            'count': len(potholes),
            'potholes': potholes,
            'timeframe': 'last_hour'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/stats')
def get_stats():
    """Get statistics about pothole detections"""
    try:
        total = PotholeDetection.query.count()
        
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent = PotholeDetection.query.filter(
            PotholeDetection.created_at >= one_hour_ago
        ).count()
        
        high_severity = PotholeDetection.query.filter_by(severity='high').count()
        medium_severity = PotholeDetection.query.filter_by(severity='medium').count()
        low_severity = PotholeDetection.query.filter_by(severity='low').count()
        
        # Calculate average confidence
        avg_confidence = 0
        if total > 0:
            avg_result = db.session.query(db.func.avg(PotholeDetection.confidence)).scalar()
            avg_confidence = avg_result if avg_result else 0
        
        stats = {
            'total': total,
            'recent': recent,
            'by_severity': {
                'high': high_severity,
                'medium': medium_severity,
                'low': low_severity
            },
            'avg_confidence': avg_confidence * 100,  # Convert to percentage
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/detection', methods=['POST'])
def add_detection():
    """Add a new pothole detection"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['latitude', 'longitude', 'confidence', 'severity']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Create new detection
        detection = PotholeDetection(
            latitude=data['latitude'],
            longitude=data['longitude'],
            confidence=data['confidence'],
            severity=data['severity'],
            timestamp=data.get('timestamp', time.time())
        )
        
        # Save to database
        db.session.add(detection)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Pothole detection saved',
            'id': detection.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/process_sensor', methods=['POST'])
def process_sensor_data():
    """Process sensor data and return detections"""
    try:
        data = request.get_json()
        
        # Extract sensor data
        timestamp = data.get('timestamp', time.time())
        x = data.get('x', 0)
        y = data.get('y', 0)
        z = data.get('z', 0)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # Process through PotholeNet API
        detections = process_real_time_data(timestamp, x, y, z, latitude, longitude)
        
        # Save detections to database
        saved_detections = []
        for detection in detections:
            db_detection = PotholeDetection(
                latitude=detection['latitude'],
                longitude=detection['longitude'],
                confidence=detection['confidence'],
                severity=detection['severity'],
                timestamp=detection['timestamp']
            )
            db.session.add(db_detection)
            saved_detections.append(db_detection)
        
        if saved_detections:
            db.session.commit()
        
        return jsonify({
            'status': 'success',
            'detections': [d.to_dict() for d in saved_detections],
            'count': len(saved_detections)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/clear', methods=['POST'])
def clear_detections():
    """Clear all pothole detections (for testing)"""
    try:
        PotholeDetection.query.delete()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'All detections cleared'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def add_sample_data():
    """Add sample pothole data for testing (Ghaziabad, India locations)"""
    sample_data = [
        {
            'latitude': 28.6692,
            'longitude': 77.4538,
            'confidence': 0.85,
            'severity': 'medium',
            'timestamp': time.time() - 3600  # 1 hour ago
        },
        {
            'latitude': 28.6700,
            'longitude': 77.4525,
            'confidence': 0.95,
            'severity': 'high',
            'timestamp': time.time() - 1800  # 30 minutes ago
        },
        {
            'latitude': 28.6685,
            'longitude': 77.4550,
            'confidence': 0.75,
            'severity': 'low',
            'timestamp': time.time() - 900  # 15 minutes ago
        },
        {
            'latitude': 28.6710,
            'longitude': 77.4540,
            'confidence': 0.80,
            'severity': 'medium',
            'timestamp': time.time() - 2700  # 45 minutes ago
        },
        {
            'latitude': 28.6675,
            'longitude': 77.4520,
            'confidence': 0.90,
            'severity': 'high',
            'timestamp': time.time() - 600  # 10 minutes ago
        }
    ]
    
    for data in sample_data:
        detection = PotholeDetection(
            latitude=data['latitude'],
            longitude=data['longitude'],
            confidence=data['confidence'],
            severity=data['severity'],
            timestamp=data['timestamp']
        )
        db.session.add(detection)
    
    db.session.commit()
    print(f"Added {len(sample_data)} sample pothole detections")

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Add sample data if database is empty
    if PotholeDetection.query.count() == 0:
        add_sample_data()
    
    print("PotholeNet Flask Application")
    print("===========================")
    print("Starting server on http://localhost:5000")
    print("API endpoints:")
    print("  GET  /api/potholes     - Get all pothole coordinates")
    print("  GET  /api/stats        - Get detection statistics")
    print("  POST /api/detection    - Add new detection")
    print("  POST /api/process_sensor - Process sensor data")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
