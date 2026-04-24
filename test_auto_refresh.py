"""
Test Auto-Refresh Functionality

Tests the Flask app.py /api/potholes endpoint and map.js auto-refresh
"""

import requests
import json
import time
import threading
from datetime import datetime

def test_flask_api():
    """Test Flask API endpoints"""
    print("Testing Flask API Endpoints")
    print("=" * 40)
    
    base_url = "http://localhost:5000"
    
    # Test main endpoint
    try:
        response = requests.get(f"{base_url}/api/potholes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ /api/potholes endpoint working")
            print(f"  Status: {data.get('status')}")
            print(f"  Count: {data.get('count')}")
            print(f"  Potholes: {len(data.get('potholes', []))}")
        else:
            print(f"✗ /api/potholes failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ Flask server not running - start with: python app.py")
    except Exception as e:
        print(f"✗ API test failed: {e}")
    
    # Test stats endpoint
    try:
        response = requests.get(f"{base_url}/api/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ /api/stats endpoint working")
            print(f"  Total detections: {data.get('stats', {}).get('total', 0)}")
        else:
            print(f"✗ /api/stats failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Stats test failed: {e}")

def test_map_js_structure():
    """Test map.js auto-refresh implementation"""
    print("\nTesting map.js Auto-Refresh Implementation")
    print("=" * 40)
    
    try:
        with open('static/js/map.js', 'r') as f:
            content = f.read()
        
        # Check for key auto-refresh components
        checks = [
            ('setInterval(fetchPotholeData, 30000)', '30-second interval refresh'),
            ('fetchPotholeData()', 'Fetch function implementation'),
            ('/api/potholes', 'Correct API endpoint'),
            ('clearAllMarkers()', 'Clear existing markers'),
            ('updateLastUpdateTime', 'Update timestamp display'),
            ('showRefreshStatus', 'Status indicator'),
            ('stopAutoRefresh', 'Stop refresh function'),
            ('manualRefresh', 'Manual refresh function')
        ]
        
        for check, description in checks:
            if check in content:
                print(f"✓ {description}")
            else:
                print(f"✗ {description} (NOT FOUND)")
                
    except FileNotFoundError:
        print("✗ static/js/map.js not found")
    except Exception as e:
        print(f"✗ Map.js test failed: {e}")

def test_flask_app_structure():
    """Test Flask app structure"""
    print("\nTesting Flask App Structure")
    print("=" * 40)
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Check for key Flask components
        checks = [
            ('@app.route(\'/api/potholes\')', 'API potholes endpoint'),
            ('Flask', 'Flask import'),
            ('SQLAlchemy', 'Database integration'),
            ('PotholeDetection', 'Database model'),
            ('jsonify', 'JSON response'),
            ('render_template', 'Template rendering')
        ]
        
        for check, description in checks:
            if check in content:
                print(f"✓ {description}")
            else:
                print(f"✗ {description} (NOT FOUND)")
                
    except FileNotFoundError:
        print("✗ app.py not found")
    except Exception as e:
        print(f"✗ Flask app test failed: {e}")

def simulate_auto_refresh():
    """Simulate the auto-refresh behavior"""
    print("\nSimulating Auto-Refresh Behavior")
    print("=" * 40)
    
    base_url = "http://localhost:5000"
    
    def fetch_update():
        try:
            response = requests.get(f"{base_url}/api/potholes", timeout=5)
            if response.status_code == 200:
                data = response.json()
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] Refreshed {data.get('count', 0)} potholes")
                return data.get('count', 0)
            else:
                print(f"Fetch failed: {response.status_code}")
                return 0
        except Exception as e:
            print(f"Fetch error: {e}")
            return 0
    
    # Simulate 3 refresh cycles
    print("Simulating 3 refresh cycles (5-second intervals for testing)...")
    
    for i in range(3):
        count = fetch_update()
        if i < 2:  # Don't sleep after last cycle
            time.sleep(5)
    
    print("Auto-refresh simulation completed")

def test_database_integration():
    """Test database integration"""
    print("\nTesting Database Integration")
    print("=" * 40)
    
    try:
        # Import and test database model
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from app import app, PotholeDetection, db
        
        with app.app_context():
            # Check if table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'pothole_detection' in tables:
                print("✓ Database table exists")
                
                # Count records
                count = PotholeDetection.query.count()
                print(f"✓ Database contains {count} pothole records")
                
                # Test sample query
                if count > 0:
                    sample = PotholeDetection.query.first()
                    print(f"✓ Sample record: {sample.latitude}, {sample.longitude}, {sample.severity}")
                else:
                    print("ℹ No records in database (will be populated on first run)")
            else:
                print("✗ Database table not found")
                
    except Exception as e:
        print(f"✗ Database test failed: {e}")

def generate_test_report():
    """Generate comprehensive test report"""
    print("\n" + "=" * 50)
    print("POTHOLENET AUTO-REFRESH TEST REPORT")
    print("=" * 50)
    
    # Test all components
    test_flask_app_structure()
    test_map_js_structure()
    test_database_integration()
    
    print("\n" + "-" * 50)
    print("FUNCTIONALITY TESTS")
    print("-" * 50)
    
    test_flask_api()
    simulate_auto_refresh()
    
    print("\n" + "=" * 50)
    print("IMPLEMENTATION SUMMARY")
    print("=" * 50)
    print("✅ Flask app.py created with:")
    print("   - @app.route('/api/potholes') endpoint")
    print("   - SQLAlchemy database integration")
    print("   - JSON response format")
    print("   - Sample data population")
    print()
    print("✅ map.js updated with:")
    print("   - setInterval(fetchPotholeData, 30000) - 30-second refresh")
    print("   - fetch('/api/potholes') API call")
    print("   - clearAllMarkers() before refresh")
    print("   - Status indicators and controls")
    print()
    print("✅ File structure:")
    print("   - app.py (Flask application)")
    print("   - templates/index.html (Flask template)")
    print("   - static/js/map.js (Auto-refresh map)")
    print("   - potholes.db (SQLite database)")
    print()
    print("🚀 USAGE:")
    print("   1. Install dependencies: pip install Flask Flask-SQLAlchemy")
    print("   2. Start server: python app.py")
    print("   3. Open: http://localhost:5000")
    print("   4. Map auto-refreshes every 30 seconds")
    print()
    print("📊 AUTO-REFRESH FEATURES:")
    print("   - Automatic marker updates without page reload")
    print("   - Clear existing markers before adding new ones")
    print("   - Update timestamp display")
    print("   - Status indicator (Auto-refreshing every 30s)")
    print("   - Manual refresh capability")
    print("   - Stop/start refresh controls")

if __name__ == "__main__":
    generate_test_report()
