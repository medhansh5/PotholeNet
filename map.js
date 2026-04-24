/**
 * PotholeNet Production Map - GitHub Pages Ready
 * 
 * Interactive map visualization for pothole detections with severity-based styling
 * Configured for production deployment with static API endpoints
 */

// Production API configuration
const PRODUCTION_API = {
    BASE_URL: 'https://shadowmap-api.onrender.com',
    ENDPOINTS: {
        POTHOLES: '/api/potholes',
        STATS: '/api/stats',
        DETECTION: '/api/detection'
    }
};

// Fallback to localhost for development
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:5000' 
    : PRODUCTION_API.BASE_URL;

// Initialize map
let map;
let markers = [];
let markerCluster;
let currentLocation;
let refreshInterval;

// Severity color mapping with 4px radius and white stroke
const severityColors = {
    'low': {
        color: '#FFD700',    // Yellow
        strokeColor: '#FFFFFF',
        radius: 4,
        strokeWeight: 1,
        fillOpacity: 0.8
    },
    'medium': {
        color: '#FFA500',    // Orange  
        strokeColor: '#FFFFFF',
        radius: 4,
        strokeWeight: 1,
        fillOpacity: 0.8
    },
    'high': {
        color: '#FF0000',    // Red
        strokeColor: '#FFFFFF', 
        radius: 4,
        strokeWeight: 1,
        fillOpacity: 0.8
    }
};

// Initialize map when page loads
function initMap() {
    // Create map centered on Ghaziabad, India
    map = L.map('pothole-map').setView([28.6692, 77.4538], 13);

    // Add tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap contributors © CARTO',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // Initialize marker cluster group
    markerCluster = L.markerClusterGroup({
        chunkedLoading: true,
        chunkProgress: function(processed, total, elapsed) {
            console.log(`Loading markers: ${processed}/${total} in ${elapsed}ms`);
        }
    });
    map.addLayer(markerCluster);

    // Get user location
    getUserLocation();

    // Start real-time updates
    startRealTimeUpdates();

    console.log('PotholeNet Production Map initialized');
    console.log(`API Base URL: ${API_BASE}`);
}

// Get user's current location
function getUserLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                currentLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                
                // Add user location marker
                L.marker([currentLocation.lat, currentLocation.lng], {
                    icon: L.divIcon({
                        className: 'user-location',
                        html: '<div style="background: #4285F4; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                        iconSize: [16, 16]
                    })
                }).addTo(map)
                .bindPopup('Your Location')
                .openPopup();
                
                // Center map on user location
                map.setView([currentLocation.lat, currentLocation.lng], 15);
            },
            (error) => {
                console.warn('Could not get user location:', error);
                // Use Ghaziabad as default location
                map.setView([28.6692, 77.4538], 13);
            }
        );
    }
}

// Create severity-based marker with 4px radius and white stroke
function createPotholeMarker(detection) {
    const severity = detection.severity || 'medium';
    const style = severityColors[severity];
    
    // Create circular marker with 4px radius
    const marker = L.circleMarker([detection.latitude, detection.longitude], {
        radius: style.radius,
        fillColor: style.color,
        color: style.strokeColor,
        weight: style.strokeWeight,
        opacity: 1,
        fillOpacity: style.fillOpacity
    });

    // Create popup content
    const popupContent = `
        <div class="pothole-popup">
            <h4>Pothole Detected</h4>
            <p><strong>Severity:</strong> <span style="color: ${style.color}; font-weight: bold;">${severity.toUpperCase()}</span></p>
            <p><strong>Confidence:</strong> ${(detection.confidence * 100).toFixed(1)}%</p>
            <p><strong>Location:</strong> ${detection.latitude.toFixed(6)}, ${detection.longitude.toFixed(6)}</p>
            <p><strong>Time:</strong> ${new Date(detection.timestamp * 1000).toLocaleString()}</p>
            ${detection.cluster_size ? `<p><strong>Cluster Size:</strong> ${detection.cluster_size} detections</p>` : ''}
        </div>
    `;

    marker.bindPopup(popupContent);

    // Add hover effect
    marker.on('mouseover', function() {
        this.setStyle({
            radius: style.radius + 2,
            fillOpacity: 1
        });
    });

    marker.on('mouseout', function() {
        this.setStyle({
            radius: style.radius,
            fillOpacity: style.fillOpacity
        });
    });

    return marker;
}

// Add pothole detection to map
function addPotholeDetection(detection) {
    const marker = createPotholeMarker(detection);
    markers.push(marker);
    markerCluster.addLayer(marker);
    
    // Auto-pan to new detection if it's near user location
    if (currentLocation) {
        const distance = calculateDistance(
            currentLocation.lat, currentLocation.lng,
            detection.latitude, detection.longitude
        );
        
        if (distance < 1000) { // Within 1km
            map.panTo([detection.latitude, detection.longitude]);
        }
    }
    
    console.log(`Added ${severity} severity pothole at ${detection.latitude}, ${detection.longitude}`);
}

// Add multiple detections at once
function addPotholeDetections(detections) {
    detections.forEach(detection => {
        addPotholeDetection(detection);
    });
    
    // Update cluster
    markerCluster.refreshClusters();
}

// Fetch pothole data from production API
async function fetchPotholeData() {
    try {
        const response = await fetch(`${API_BASE}${PRODUCTION_API.ENDPOINTS.POTHOLES}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'success' || result.potholes) {
            // Clear existing markers before adding new ones
            clearAllMarkers();
            
            // Add new detections
            const detections = result.potholes || result;
            addPotholeDetections(detections);
            
            // Update last update time
            updateLastUpdateTime(result.last_updated || new Date().toISOString());
            
            console.log(`Refreshed ${detections.length} pothole markers`);
            updateMapStats(detections.length);
        } else {
            console.error('API error:', result.message || 'Unknown error');
        }
        
    } catch (error) {
        console.error('Error fetching pothole data:', error);
        // Show error status in UI
        updateConnectionStatus(false);
    }
}

// Update map statistics
function updateMapStats(count) {
    const totalElement = document.getElementById('total-detections');
    if (totalElement) {
        totalElement.textContent = count;
    }
    
    updateConnectionStatus(true);
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    const statusIndicator = document.querySelector('.status-indicator');
    
    if (statusElement && statusIndicator) {
        if (connected) {
            statusElement.textContent = 'Connected';
            statusIndicator.className = 'status-indicator status-connected';
        } else {
            statusElement.textContent = 'Disconnected';
            statusIndicator.className = 'status-indicator status-disconnected';
        }
    }
}

// Update last update time display
function updateLastUpdateTime(lastUpdated) {
    const lastUpdateElement = document.getElementById('last-update');
    if (lastUpdateElement) {
        const updateTime = new Date(lastUpdated);
        lastUpdateElement.textContent = `Last update: ${updateTime.toLocaleTimeString()}`;
    }
}

// Start real-time updates with auto-refresh
function startRealTimeUpdates() {
    // Initial data load
    fetchPotholeData();
    
    // Set up auto-refresh every 30 seconds
    console.log('Starting auto-refresh: fetching pothole data every 30 seconds');
    refreshInterval = setInterval(fetchPotholeData, 30000);
    
    // Show refresh status
    showRefreshStatus(true);
}

// Show refresh status indicator
function showRefreshStatus(isActive) {
    const statusElement = document.getElementById('connection-status');
    const statusIndicator = document.querySelector('.status-indicator');
    
    if (statusElement && statusIndicator) {
        if (isActive) {
            statusElement.textContent = 'Auto-refreshing every 30s';
            statusIndicator.className = 'status-indicator status-connected';
        } else {
            statusElement.textContent = 'Auto-refresh stopped';
            statusIndicator.className = 'status-indicator status-disconnected';
        }
    }
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
        showRefreshStatus(false);
        console.log('Auto-refresh stopped');
    }
}

// Manual refresh function
function manualRefresh() {
    console.log('Manual refresh triggered');
    fetchPotholeData();
}

// Clear all markers
function clearAllMarkers() {
    markers.forEach(marker => {
        markerCluster.removeLayer(marker);
    });
    markers = [];
}

// Calculate distance between two points (meters)
function calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371000; // Earth's radius in meters
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Filter markers by severity
function filterBySeverity(severity) {
    markers.forEach(marker => {
        if (severity === 'all') {
            markerCluster.addLayer(marker);
        } else {
            // Would need to store severity info with markers for proper filtering
            markerCluster.removeLayer(marker);
        }
    });
}

// Export functions for external use
window.PotholeMap = {
    initMap,
    addPotholeDetection,
    addPotholeDetections,
    fetchPotholeData,
    filterBySeverity,
    clearAllMarkers,
    calculateDistance,
    startRealTimeUpdates,
    stopAutoRefresh,
    manualRefresh
};

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('pothole-map')) {
        initMap();
    }
});
