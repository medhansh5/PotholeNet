"""
PotholeNet v2.2 - Background Clustering Worker

Optimized background service for continuous telemetry processing
without blocking main ingestion pipeline.
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime, timedelta
from clustering_service import ClusteringService, TelemetryPoint, BackgroundClusterWorker
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelemetryDataSource:
    """Data source for raw telemetry points"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        
    async def get_pending_telemetry(self, limit: int = 1000, 
                                  since_timestamp: float = None) -> list:
        """
        Get pending telemetry points that haven't been clustered
        
        Args:
            limit: Maximum number of points to process
            since_timestamp: Only get points after this time
            
        Returns:
            List of TelemetryPoint objects
        """
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                port=self.db_config.get('port', 5432)
            )
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query
                query = """
                    SELECT 
                        id,
                        device_id,
                        timestamp,
                        latitude,
                        longitude,
                        z_magnitude,
                        speed_kmh
                    FROM raw_telemetry
                    WHERE clustered = FALSE OR clustered IS NULL
                """
                params = []
                
                if since_timestamp:
                    query += " AND timestamp >= %s"
                    params.append(since_timestamp)
                
                query += " ORDER BY timestamp ASC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                # Convert to TelemetryPoint objects
                telemetry_points = []
                for row in rows:
                    point = TelemetryPoint(
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        z_magnitude=float(row['z_magnitude']),
                        timestamp=float(row['timestamp']),
                        device_id=row['device_id'],
                        speed_kmh=float(row['speed_kmh']) if row['speed_kmh'] else None
                    )
                    telemetry_points.append(point)
                
                logger.info(f"Retrieved {len(telemetry_points)} pending telemetry points")
                return telemetry_points
                
        except Exception as e:
            logger.error(f"Error retrieving telemetry: {str(e)}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    async def mark_telemetry_clustered(self, telemetry_ids: list, event_id: str):
        """Mark telemetry points as clustered"""
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                port=self.db_config.get('port', 5432)
            )
            
            with conn.cursor() as cur:
                # Update clustered status
                query = """
                    UPDATE raw_telemetry 
                    SET clustered = TRUE, 
                        clustered_at = CURRENT_TIMESTAMP,
                        event_id = %s
                    WHERE id = ANY(%s)
                """
                cur.execute(query, [event_id, telemetry_ids])
                conn.commit()
                
                logger.info(f"Marked {len(telemetry_ids)} points as clustered for event {event_id}")
                
        except Exception as e:
            logger.error(f"Error marking telemetry as clustered: {str(e)}")
        finally:
            if 'conn' in locals():
                conn.close()

class ProductionClusteringWorker:
    """Production-ready background clustering worker"""
    
    def __init__(self, db_config: dict, 
                 eps_meters: float = 5.0, 
                 min_samples: int = 3,
                 batch_size: int = 1000,
                 processing_interval: int = 30):
        """
        Initialize clustering worker
        
        Args:
            db_config: Database connection parameters
            eps_meters: DBSCAN epsilon distance in meters
            min_samples: Minimum points for cluster formation
            batch_size: Number of telemetry points to process per batch
            processing_interval: Seconds between processing cycles
        """
        self.db_config = db_config
        self.eps_meters = eps_meters
        self.min_samples = min_samples
        self.batch_size = batch_size
        self.processing_interval = processing_interval
        
        # Initialize services
        self.clustering_service = ClusteringService(eps_meters, min_samples)
        self.telemetry_source = TelemetryDataSource(db_config)
        
        # Worker state
        self.is_running = False
        self.last_processed_timestamp = 0
        self.stats = {
            'total_processed': 0,
            'total_events_created': 0,
            'processing_cycles': 0,
            'errors': 0,
            'start_time': None
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.is_running = False
    
    async def start(self):
        """Start the background clustering worker"""
        self.is_running = True
        self.stats['start_time'] = datetime.utcnow()
        
        logger.info("Starting PotholeNet v2.2 Background Clustering Worker")
        logger.info(f"Configuration: eps={self.eps_meters}m, min_samples={self.min_samples}")
        logger.info(f"Batch size: {self.batch_size}, Interval: {self.processing_interval}s")
        
        try:
            while self.is_running:
                await self._processing_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.processing_interval)
                
        except Exception as e:
            logger.error(f"Worker error: {str(e)}")
        finally:
            await self._shutdown()
    
    async def _processing_cycle(self):
        """Single processing cycle"""
        cycle_start = datetime.utcnow()
        self.stats['processing_cycles'] += 1
        
        try:
            # Get pending telemetry data
            telemetry_points = await self.telemetry_source.get_pending_telemetry(
                limit=self.batch_size,
                since_timestamp=self.last_processed_timestamp
            )
            
            if not telemetry_points:
                logger.debug("No pending telemetry points to process")
                return
            
            # Process clustering
            road_events = await self.clustering_service.process_pending_telemetry(telemetry_points)
            
            # Store events and update telemetry
            await self._store_road_events(road_events, telemetry_points)
            
            # Update statistics
            self.stats['total_processed'] += len(telemetry_points)
            self.stats['total_events_created'] += len(road_events)
            
            # Update last processed timestamp
            if telemetry_points:
                self.last_processed_timestamp = max(point.timestamp for point in telemetry_points)
            
            cycle_time = (datetime.utcnow() - cycle_start).total_seconds()
            logger.info(f"Processing cycle completed in {cycle_time:.2f}s: "
                        f"{len(telemetry_points)} points -> {len(road_events)} events")
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error in processing cycle: {str(e)}")
    
    async def _store_road_events(self, road_events: list, telemetry_points: list):
        """Store road events and update telemetry status"""
        if not road_events:
            return
        
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                port=self.db_config.get('port', 5432)
            )
            
            with conn.cursor() as cur:
                for event in road_events:
                    # Insert road event
                    event_query = """
                        INSERT INTO road_events (
                            event_id, center_latitude, center_longitude, radius_meters,
                            point_count, avg_z_magnitude, max_z_magnitude,
                            confidence_score, severity, start_time, end_time,
                            device_ids, road_health_impact, cluster_algorithm,
                            eps_meters, min_samples
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """
                    
                    cur.execute(event_query, [
                        event.event_id, event.center_lat, event.center_lng,
                        event.radius_meters, event.point_count, event.avg_z_magnitude,
                        event.max_z_magnitude, event.confidence_score, event.severity,
                        event.start_time, event.end_time, event.device_ids,
                        event.road_health_impact, 'DBSCAN', self.eps_meters, self.min_samples
                    ])
                    
                    event_db_id = cur.fetchone()[0]
                    
                    # Link telemetry points to event
                    if event.device_ids:
                        # Get telemetry IDs for this event's devices
                        device_ids = event.device_ids if isinstance(event.device_ids, list) else [event.device_ids]
                        
                        telemetry_query = """
                            UPDATE raw_telemetry 
                            SET clustered = TRUE, 
                                clustered_at = CURRENT_TIMESTAMP,
                                event_id = %s
                            WHERE device_id = ANY(%s) 
                                AND timestamp >= %s 
                                AND timestamp <= %s
                        """
                        
                        cur.execute(telemetry_query, [
                            event.event_id, device_ids,
                            event.start_time, event.end_time
                        ])
                
                conn.commit()
                logger.info(f"Stored {len(road_events)} road events in database")
                
        except Exception as e:
            logger.error(f"Error storing road events: {str(e)}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    async def _shutdown(self):
        """Graceful shutdown of worker"""
        logger.info("Shutting down clustering worker...")
        
        # Print final statistics
        if self.stats['start_time']:
            runtime = datetime.utcnow() - self.stats['start_time']
            logger.info("=== Final Statistics ===")
            logger.info(f"Runtime: {runtime}")
            logger.info(f"Processing cycles: {self.stats['processing_cycles']}")
            logger.info(f"Total telemetry processed: {self.stats['total_processed']}")
            logger.info(f"Total events created: {self.stats['total_events_created']}")
            logger.info(f"Errors encountered: {self.stats['errors']}")
            
            if self.stats['total_processed'] > 0:
                efficiency = self.stats['total_events_created'] / self.stats['total_processed']
                logger.info(f"Clustering efficiency: {efficiency:.2%} events per point")

# Configuration from environment variables
def get_db_config():
    """Get database configuration from environment"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'potholenet'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password'),
        'port': int(os.getenv('DB_PORT', 5432))
    }

async def main():
    """Main entry point for background worker"""
    # Get configuration
    db_config = get_db_config()
    
    # Worker configuration from environment
    eps_meters = float(os.getenv('CLUSTER_EPS_METERS', '5.0'))
    min_samples = int(os.getenv('CLUSTER_MIN_SAMPLES', '3'))
    batch_size = int(os.getenv('CLUSTER_BATCH_SIZE', '1000'))
    processing_interval = int(os.getenv('CLUSTER_INTERVAL_SECONDS', '30'))
    
    # Create and start worker
    worker = ProductionClusteringWorker(
        db_config=db_config,
        eps_meters=eps_meters,
        min_samples=min_samples,
        batch_size=batch_size,
        processing_interval=processing_interval
    )
    
    await worker.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
