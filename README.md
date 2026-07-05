# PotholeNet v3.0.0 - Real-time Road Quality Mapping

> **High-performance edge computing and infrastructure monitoring through spatial aggregation, native signal processing, and machine learning**

---

## Project Vision

PotholeNet transforms mobile devices and edge telemetry units into intelligent road quality sensors. By processing high-frequency accelerometer data at the edge and aggregating detections through spatial clustering, we create real-time maps of road infrastructure health for municipalities and navigation systems.

**Core Innovation**: Sub-millisecond signal processing and ML inference on-device with cloud-based spatial aggregation for scalable, privacy-preserving road monitoring.

---

## Architecture: The Three Pillars

### 🎯 **The Edge (C++17 & ML Engine)**
**High-frequency signal processing with deterministic latency & Random Forest classification**

- **4th-order Butterworth High-Pass Filter**: Implemented via numerically stable **Biquad Second-Order Sections (SOS) cascade** (12Hz cutoff) to eliminate vehicle suspension and engine vibration.
- **Zero-allocation Hot Path**: Circular ring buffers with modulo power-of-2 index wrapping ensuring sub-millisecond processing (~0.15ms/sample).
- **7-Feature ML Schema**: Real-time computation of $Z$-axis variance, peak-to-peak amplitude, RMS, maximum absolute acceleration, lateral $XY$-RMS, high-frequency spectral power (20-50Hz), and spectral centroid.
- **Random Forest Inference**: On-device classification with calibrated supermajority voting for robust anomaly detection.

```
potholenet_core.cpp / engine.py   // 100Hz+ processing, <0.2ms latency
├── ButterworthFilter (SOS)       // 12Hz cutoff, 4th-order Biquad cascade
├── SignalProcessor               // Circular ring buffers, 7-feature schema
├── PotholeClassifier             // Random Forest ML model (v3.0.0)
└── FFI Interface                 // C-compatible exports across ABI boundaries
```

### 🌉 **The Bridge & APIs (Dart FFI & Flask REST)**
**Low-overhead communication between native code, backend services, and visualization UI**

- **C-compatible FFI Layer**: Exception-safe `extern "C"` exports with automated lifecycle management for mobile apps (Flutter/Dart).
- **Thread-safe REST & WebSocket APIs**: Built on Flask with $O(1)$ `collections.deque` buffers, non-blocking coroutine execution, and strict CORS policies.
- **Dynamic Web Visualization**: Interactive Leaflet map dashboard (`map.js` & `index.html`) featuring color-coded severity markers (Yellow/Low, Orange/Medium, Red/High), auto-refresh cycles, and dark mode styling.

```
/api/v2/map/clusters     // GeoJSON road events & severity clusters
/api/v2/health/score     // Area geographical health metrics
/api/v2/clustering/stats // Real-time performance analytics
/api/potholes            // Live telemetry feed & auto-refresh endpoint
```

### 🧠 **The Brain (PostgreSQL/PostGIS & scikit-learn DBSCAN)**
**Spatial clustering and geographical health scoring**

- **BallTree DBSCAN Clustering**: Fast $O(N \log N)$ spatial clustering using scikit-learn BallTree metrics, replacing slow $O(N^2)$ Haversine loops.
- **PostGIS Spatial Schema**: Optimized spatial indexing with immutable geometry predicates and non-blocking background worker ingestion.
- **Road Health Scoring**: Dynamic geographical health scoring (0-100 scale) based on cluster density, severity distribution, and telemetry frequency.

---

## Technical Stack

| Layer | Technology | Purpose |
|--------|-------------|----------|
| **Edge Core** | C++17, CMake, Android NDK | Native signal processing, SOS Biquad filter, FFI exports |
| **ML Engine** | Python, scikit-learn, NumPy, Pandas | 7-feature extraction, Random Forest training & live inference |
| **Backend API** | Python, Flask, SQLAlchemy | REST server, thread-safe buffers, non-blocking DB queries |
| **Database** | PostgreSQL + PostGIS | Spatial indexing, immutable geometries, DBSCAN cluster storage |
| **Frontend** | HTML5, Vanilla CSS, Leaflet.js | Real-time map dashboard, severity filtering, auto-refresh UI |
| **Mobile Bridge**| Dart FFI / Flutter | Cross-platform mobile interface and native DLL/.so loading |

---

## Performance Benchmarks

### Edge Processing (C++ / ML Engine)
```
Sample Rate:        100 Hz
Processing Time:     ~0.15ms per sample
Latency:            <0.2ms worst-case
Memory Usage:        ~2KB per processor instance
Throughput:          >11,000 samples/second
Allocations:         0 in hot path (pre-allocated ring buffers)
```

### Spatial Aggregation (BallTree DBSCAN & PostGIS)
```
Clustering Algorithm: scikit-learn BallTree DBSCAN (ε=5m, min_samples=3)
Complexity:         O(N log N) spatial query time
Index Type:         PostGIS GIST with immutable predicates
Query Performance:    <50ms for city-scale geographical queries
Storage Efficiency:   >90% reduction vs raw telemetry ingestion
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- Visual Studio 2019+ / GCC / Clang (for native C++ core compilation)
- CMake 3.16+
- PostgreSQL 13+ with PostGIS extension (for production spatial storage)

### 1. Build Native Core
```bash
# Clone repository
git clone https://github.com/medhansh5/potholenet.git
cd potholenet

# Build Windows DLL (from VS Developer Command Prompt or PowerShell)
build_windows.bat

# Or build Android native libraries (.so)
bash build_android.sh
```

### 2. Backend & ML Setup
```bash
# Create and activate Python virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run data validation & model training
python scripts/data_validator.py
python scripts/train_model.py
```

### 3. Start Web Dashboard & Server
```bash
# Start the backend server and API
python web_server.py
# Or start the Flask auto-refresh server
python app.py

# Open your browser at:
# http://localhost:8000 or http://localhost:5000
```

---

## Development Workflow & Testing

### Run Automated Test Suite
PotholeNet includes a comprehensive unit and integration test suite across all architectural layers:

```bash
# Run ML Engine & Signal Processing tests (16 tests)
python test_engine.py

# Run Leaflet Map Marker styling & API integration tests
python test_map_markers.py

# Run Flask API & Auto-Refresh structure tests
python test_auto_refresh.py
```

---

## API Reference

### Core FFI Functions (`potholenet_core.h`)
```c
// Lifecycle
void* create_processor(double frequency, double cutoff);
bool process_sample(void* processor, double x, double y, double z);
void destroy_processor(void* processor);

// Feature Extraction
double get_current_magnitude(void* processor);
double get_z_variance(void* processor);
double get_peak_to_peak(void* processor);
```

### REST Endpoints
```http
GET /api/v2/map/clusters?bounds={}&severity={}&time_range={}
GET /api/v2/health/score?bounds={}
GET /api/v2/clustering/stats
GET /api/potholes
```

---

## Architecture Deep Dive

### Signal Processing & ML Pipeline
```
Raw Accelerometer (100Hz) → Butterworth HPF (12Hz SOS Biquad) → 7-Feature Schema
                                                                      ↓
PotholeDetection GeoJSON ← Random Forest Classifier (v3.0.0) ← Sliding Window (100 samples)
```

### Spatial Aggregation Pipeline
```
Mobile Telemetry Feed → Non-blocking DB Ingest → BallTree DBSCAN Clustering → Road Events
                              ↓                          ↓                        ↓
                      PostgreSQL/PostGIS        GIST Spatial Index      Leaflet UI Dashboard
```

---

## Contributing Guidelines

### Code Standards
- **C++17 compliance** with portable standard library usage and zero exception leakage across FFI boundaries.
- **Zero-allocation hot paths** for real-time telemetry processing.
- **Comprehensive testing** ensuring all unit tests and performance benchmarks pass.
- **Cross-platform validation** across Windows, Android, and Linux environments.

### Submission Process
1. Fork the repository and create a feature branch (`feature/amazing-feature`).
2. Implement changes with accompanying tests.
3. Validate performance benchmarks and verify formatting.
4. Submit a pull request with technical rationale and verification results.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**PotholeNet v3.0.0** - Engineering-grade real-time infrastructure monitoring through native edge computing, machine learning, and intelligent spatial aggregation.

> Built with ❤️ for safer roads worldwide
