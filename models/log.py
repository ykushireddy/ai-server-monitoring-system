"""
Log model for storing application events and audit trail.
"""

from datetime import datetime
from enum import Enum
from models.metric import db


class EventType(str, Enum):
    """Types of events that can be logged."""
    METRIC_COLLECTION = 'metric_collection'
    ALERT_CREATED = 'alert_created'
    ALERT_ACKNOWLEDGED = 'alert_acknowledged'
    ALERT_RESOLVED = 'alert_resolved'
    ANOMALY_DETECTED = 'anomaly_detected'
    ML_TRAINING = 'ml_training'
    EMAIL_SENT = 'email_sent'
    EMAIL_FAILED = 'email_failed'
    REPORT_GENERATED = 'report_generated'
    SYSTEM_START = 'system_start'
    SYSTEM_ERROR = 'system_error'
    CONFIG_CHANGE = 'config_change'


class Log(db.Model):
    """
    Stores application events for audit and debugging.
    
    Attributes:
        id: Primary key
        event_type: Type of event (from EventType enum)
        description: Human-readable event description
        details_json: Optional JSON with additional event details
        severity: Log level (debug, info, warning, error, critical)
        source: Component that generated the log
        created_at: When the event occurred
    """
    
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    details_json = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), nullable=False, default='info', index=True)
    source = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Log {self.id} [{self.event_type}] {self.description[:50]}>"
    
    def to_dict(self):
        """Convert log to dictionary for JSON serialization."""
        import json
        return {
            'id': self.id,
            'event_type': self.event_type,
            'description': self.description,
            'details': json.loads(self.details_json) if self.details_json else None,
            'severity': self.severity,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def create(cls, event_type, description, details=None, severity='info', source=None):
        """
        Create and save a new log entry.
        
        Args:
            event_type: Type of event (EventType enum or string)
            description: Human-readable description
            details: Optional dictionary with additional details
            severity: Log level
            source: Component name that generated the log
            
        Returns:
            Created Log instance
        """
        import json
        
        if isinstance(event_type, EventType):
            event_type = event_type.value
        
        log = cls(
            event_type=event_type,
            description=description,
            details_json=json.dumps(details) if details else None,
            severity=severity,
            source=source
        )
        
        db.session.add(log)
        db.session.commit()
        
        return log
    
    @classmethod
    def get_recent(cls, hours=24, event_type=None, severity=None, limit=100):
        """Get recent log entries with optional filters."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        query = cls.query.filter(cls.created_at >= cutoff)
        
        if event_type:
            if isinstance(event_type, EventType):
                event_type = event_type.value
            query = query.filter(cls.event_type == event_type)
        
        if severity:
            query = query.filter(cls.severity == severity)
        
        return query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def search(cls, query_text, hours=24, limit=100):
        """Search logs by description text."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return cls.query.filter(
            cls.created_at >= cutoff,
            cls.description.ilike(f'%{query_text}%')
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_statistics(cls, hours=24):
        """Get log statistics for the specified period."""
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        type_counts = db.session.query(
            cls.event_type,
            func.count(cls.id)
        ).filter(cls.created_at >= cutoff).group_by(cls.event_type).all()
        
        severity_counts = db.session.query(
            cls.severity,
            func.count(cls.id)
        ).filter(cls.created_at >= cutoff).group_by(cls.severity).all()
        
        return {
            'by_type': {t: c for t, c in type_counts},
            'by_severity': {s: c for s, c in severity_counts},
            'total': sum(c for _, c in type_counts)
        }
