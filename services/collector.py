"""
Metrics collection service using psutil.
Collects system metrics: CPU, memory, disk, network, processes, uptime.
"""

import os
import psutil
import time
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects system metrics using psutil library.
    
    Maintains state for calculating network rates between collections.
    """
    
    def __init__(self):
        """Initialize the collector with baseline network counters."""
        self._last_network_counters = None
        self._last_collection_time = None
        self._initialize_network_baseline()
    
    def _initialize_network_baseline(self):
        """Set initial network counters for rate calculation."""
        try:
            counters = psutil.net_io_counters()
            self._last_network_counters = {
                'bytes_sent': counters.bytes_sent,
                'bytes_recv': counters.bytes_recv
            }
            self._last_collection_time = time.time()
        except Exception as e:
            logger.warning(f"Failed to initialize network baseline: {e}")
            self._last_network_counters = {'bytes_sent': 0, 'bytes_recv': 0}
            self._last_collection_time = time.time()
    
    def collect(self) -> Dict:
        """
        Collect all system metrics.
        
        Returns:
            Dictionary containing:
            - cpu_usage: CPU percentage (0-100)
            - memory_usage: Memory percentage (0-100)
            - disk_usage: Disk percentage (0-100)
            - network_sent: Total bytes sent
            - network_received: Total bytes received
            - network_sent_rate: Upload rate in bytes/second
            - network_received_rate: Download rate in bytes/second
            - process_count: Number of running processes
            - uptime_seconds: System uptime in seconds
            - health_score: Computed health score (0-100)
            - timestamp: Collection timestamp
        """
        metrics = {}
        
        # CPU usage (averaged over a short interval for accuracy)
        try:
            metrics['cpu_usage'] = psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.error(f"Failed to collect CPU metrics: {e}")
            metrics['cpu_usage'] = 0.0
        
        # Memory usage
        try:
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = memory.percent
        except Exception as e:
            logger.error(f"Failed to collect memory metrics: {e}")
            metrics['memory_usage'] = 0.0
        
        # Disk usage (root / system drive)
        try:
            disk_path = os.environ.get('DISK_PATH') or ('C:\\' if os.name == 'nt' else '/')
            disk = psutil.disk_usage(disk_path)
            metrics['disk_usage'] = disk.percent
        except Exception as e:
            logger.error(f"Failed to collect disk metrics: {e}")
            metrics['disk_usage'] = 0.0
        
        # Network metrics with rate calculation
        try:
            net_counters = psutil.net_io_counters()
            current_time = time.time()
            
            metrics['network_sent'] = net_counters.bytes_sent
            metrics['network_received'] = net_counters.bytes_recv
            
            # Calculate rates
            if self._last_network_counters and self._last_collection_time:
                time_delta = current_time - self._last_collection_time
                if time_delta > 0:
                    bytes_sent_delta = net_counters.bytes_sent - self._last_network_counters['bytes_sent']
                    bytes_recv_delta = net_counters.bytes_recv - self._last_network_counters['bytes_recv']
                    
                    metrics['network_sent_rate'] = max(0, bytes_sent_delta / time_delta)
                    metrics['network_received_rate'] = max(0, bytes_recv_delta / time_delta)
                else:
                    metrics['network_sent_rate'] = 0.0
                    metrics['network_received_rate'] = 0.0
            else:
                metrics['network_sent_rate'] = 0.0
                metrics['network_received_rate'] = 0.0
            
            # Update baseline for next collection
            self._last_network_counters = {
                'bytes_sent': net_counters.bytes_sent,
                'bytes_recv': net_counters.bytes_recv
            }
            self._last_collection_time = current_time
            
        except Exception as e:
            logger.error(f"Failed to collect network metrics: {e}")
            metrics['network_sent'] = 0.0
            metrics['network_received'] = 0.0
            metrics['network_sent_rate'] = 0.0
            metrics['network_received_rate'] = 0.0
        
        # Process count
        try:
            metrics['process_count'] = len(psutil.pids())
        except Exception as e:
            logger.error(f"Failed to collect process count: {e}")
            metrics['process_count'] = 0
        
        # System uptime
        try:
            boot_time = psutil.boot_time()
            metrics['uptime_seconds'] = time.time() - boot_time
        except Exception as e:
            logger.error(f"Failed to collect uptime: {e}")
            metrics['uptime_seconds'] = 0.0
        
        # Calculate health score
        from models.metric import Metric
        metrics['health_score'] = Metric.calculate_health_score(
            metrics['cpu_usage'],
            metrics['memory_usage'],
            metrics['disk_usage']
        )
        
        # Add timestamp
        metrics['timestamp'] = datetime.utcnow()
        
        logger.debug(f"Collected metrics: CPU={metrics['cpu_usage']:.1f}%, "
                    f"MEM={metrics['memory_usage']:.1f}%, DISK={metrics['disk_usage']:.1f}%")
        
        return metrics
    
    def collect_and_store(self, db_session) -> Optional['Metric']:
        """
        Collect metrics and store them in the database.
        
        Args:
            db_session: SQLAlchemy database session
            
        Returns:
            Created Metric instance or None on failure
        """
        from models.metric import Metric
        
        try:
            data = self.collect()
            
            metric = Metric(
                cpu_usage=data['cpu_usage'],
                memory_usage=data['memory_usage'],
                disk_usage=data['disk_usage'],
                network_sent=data['network_sent'],
                network_received=data['network_received'],
                network_sent_rate=data['network_sent_rate'],
                network_received_rate=data['network_received_rate'],
                process_count=data['process_count'],
                uptime_seconds=data['uptime_seconds'],
                health_score=data['health_score'],
                created_at=data['timestamp']
            )
            
            db_session.add(metric)
            db_session.commit()
            
            logger.info(f"Stored metric {metric.id}: health_score={metric.health_score:.1f}")
            
            return metric
            
        except Exception as e:
            logger.error(f"Failed to collect and store metrics: {e}")
            db_session.rollback()
            return None
    
    @staticmethod
    def get_system_info() -> Dict:
        """
        Get static system information.
        
        Returns:
            Dictionary with system details
        """
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'memory_total': psutil.virtual_memory().total,
                'disk_total': psutil.disk_usage(
                    os.environ.get('DISK_PATH') or ('C:\\' if os.name == 'nt' else '/')
                ).total,
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'platform': {
                    'system': psutil.LINUX if hasattr(psutil, 'LINUX') else 'unknown',
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}
    
    @staticmethod
    def format_bytes(bytes_value: float) -> str:
        """Format bytes into human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_value) < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    @staticmethod
    def format_uptime(seconds: float) -> str:
        """Format uptime seconds into human-readable string."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")
        
        return " ".join(parts)
