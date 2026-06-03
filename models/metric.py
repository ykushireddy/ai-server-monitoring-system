"""
Metric model for storing server monitoring data.
Captures CPU, memory, disk, network metrics and computed health scores.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
class Metric(db.Model):
    """
    Stores point-in-time server metrics.
    
    Attributes:
        id: Primary key
        cpu_usage: CPU utilization percentage (0-100)
        memory_usage: Memory utilization percentage (0-100)
        disk_usage: Disk utilization percentage (0-100)
        network_sent: Network bytes sent since last reading
        network_received: Network bytes received since last reading
        network_sent_rate: Network upload rate in bytes/second
        network_received_rate: Network download rate in bytes/second
        process_count: Number of running processes
        uptime_seconds: System uptime in seconds
        health_score: Computed overall health score (0-100, higher is better)
        created_at: Timestamp when metric was recorded
    """
    
    __tablename__ = 'metrics'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cpu_usage = db.Column(db.Float, nullable=False, index=True)
    memory_usage = db.Column(db.Float, nullable=False, index=True)
    disk_usage = db.Column(db.Float, nullable=False)
    network_sent = db.Column(db.Float, nullable=False, default=0.0)
    network_received = db.Column(db.Float, nullable=False, default=0.0)
    network_sent_rate = db.Column(db.Float, nullable=False, default=0.0)
    network_received_rate = db.Column(db.Float, nullable=False, default=0.0)
    process_count = db.Column(db.Integer, nullable=False, default=0)
    uptime_seconds = db.Column(db.Float, nullable=False, default=0.0)
    health_score = db.Column(db.Float, nullable=False, default=100.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Metric {self.id} CPU:{self.cpu_usage:.1f}% MEM:{self.memory_usage:.1f}% at {self.created_at}>"
    
    def to_dict(self):
        """Convert metric to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'cpu_usage': round(self.cpu_usage, 2),
            'memory_usage': round(self.memory_usage, 2),
            'disk_usage': round(self.disk_usage, 2),
            'network_sent': round(self.network_sent, 2),
            'network_received': round(self.network_received, 2),
            'network_sent_rate': round(self.network_sent_rate, 2),
            'network_received_rate': round(self.network_received_rate, 2),
            'process_count': self.process_count,
            'uptime_seconds': round(self.uptime_seconds, 2),
            'health_score': round(self.health_score, 2),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def calculate_health_score(cpu_usage, memory_usage, disk_usage):
        """
        Calculate overall system health score.
        
        Score is weighted: CPU (40%), Memory (35%), Disk (25%)
        Higher usage = lower health score.
        
        Args:
            cpu_usage: CPU percentage (0-100)
            memory_usage: Memory percentage (0-100)
            disk_usage: Disk percentage (0-100)
            
        Returns:
            Health score from 0 (critical) to 100 (healthy)
        """
        # Invert percentages (100% usage = 0 health contribution)
        cpu_health = max(0, 100 - cpu_usage)
        memory_health = max(0, 100 - memory_usage)
        disk_health = max(0, 100 - disk_usage)
        
        # Weighted average
        health_score = (cpu_health * 0.40) + (memory_health * 0.35) + (disk_health * 0.25)
        
        return round(health_score, 2)
    
    @classmethod
    def get_latest(cls):
        """Get the most recent metric record."""
        return cls.query.order_by(cls.created_at.desc()).first()
    
    @classmethod
    def get_history(cls, hours=1, limit=None):
        """
        Get metrics for the specified time period.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of records to return
            
        Returns:
            List of Metric objects ordered by timestamp ascending
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = cls.query.filter(cls.created_at >= cutoff).order_by(cls.created_at.asc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @classmethod
    def get_statistics(cls, hours=24):
        """
        Calculate statistics for metrics over the specified period.
        
        Returns:
            Dictionary with min, max, avg for each metric type
        """
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        stats = db.session.query(
            func.min(cls.cpu_usage).label('cpu_min'),
            func.max(cls.cpu_usage).label('cpu_max'),
            func.avg(cls.cpu_usage).label('cpu_avg'),
            func.min(cls.memory_usage).label('memory_min'),
            func.max(cls.memory_usage).label('memory_max'),
            func.avg(cls.memory_usage).label('memory_avg'),
            func.min(cls.disk_usage).label('disk_min'),
            func.max(cls.disk_usage).label('disk_max'),
            func.avg(cls.disk_usage).label('disk_avg'),
            func.avg(cls.health_score).label('health_avg'),
            func.count(cls.id).label('total_records')
        ).filter(cls.created_at >= cutoff).first()
        
        if not stats or stats.total_records == 0:
            return None
            
        return {
            'cpu': {
                'min': round(stats.cpu_min or 0, 2),
                'max': round(stats.cpu_max or 0, 2),
                'avg': round(stats.cpu_avg or 0, 2)
            },
            'memory': {
                'min': round(stats.memory_min or 0, 2),
                'max': round(stats.memory_max or 0, 2),
                'avg': round(stats.memory_avg or 0, 2)
            },
            'disk': {
                'min': round(stats.disk_min or 0, 2),
                'max': round(stats.disk_max or 0, 2),
                'avg': round(stats.disk_avg or 0, 2)
            },
            'health_avg': round(stats.health_avg or 0, 2),
            'total_records': stats.total_records,
        }