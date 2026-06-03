"""
Alert model for threshold and ML-driven notifications.
"""

from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import func

from models.metric import db


class AlertSeverity(str, Enum):
    CRITICAL = 'critical'
    WARNING = 'warning'
    INFO = 'info'


class AlertStatus(str, Enum):
    ACTIVE = 'active'
    ACKNOWLEDGED = 'acknowledged'
    RESOLVED = 'resolved'


class Alert(db.Model):
    """Stores monitoring alerts and their lifecycle."""

    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    metric_name = db.Column(db.String(50), nullable=False, index=True)
    metric_value = db.Column(db.Float, nullable=False)
    severity = db.Column(db.String(20), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=AlertStatus.ACTIVE.value, index=True)
    anomaly_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Alert {self.id} [{self.severity}] {self.metric_name}={self.metric_value:.1f}>"

    def to_dict(self):
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': round(self.metric_value, 2),
            'severity': self.severity,
            'message': self.message,
            'status': self.status,
            'anomaly_score': round(self.anomaly_score, 4) if self.anomaly_score is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def acknowledge(self):
        self.status = AlertStatus.ACKNOWLEDGED.value
        self.acknowledged_at = datetime.utcnow()
        db.session.commit()

    def resolve(self):
        self.status = AlertStatus.RESOLVED.value
        self.resolved_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def get_active_alerts(cls):
        return cls.query.filter(cls.status == AlertStatus.ACTIVE.value).order_by(
            cls.created_at.desc()
        ).all()

    @classmethod
    def get_active_count(cls):
        return cls.query.filter(cls.status == AlertStatus.ACTIVE.value).count()

    @classmethod
    def get_recent_alerts(cls, hours=24, limit=100):
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return cls.query.filter(cls.created_at >= cutoff).order_by(
            cls.created_at.desc()
        ).limit(limit).all()

    @classmethod
    def get_statistics(cls, hours=24):
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        total = cls.query.filter(cls.created_at >= cutoff).count()

        severity_counts = db.session.query(
            cls.severity, func.count(cls.id)
        ).filter(cls.created_at >= cutoff).group_by(cls.severity).all()

        status_counts = db.session.query(
            cls.status, func.count(cls.id)
        ).filter(cls.created_at >= cutoff).group_by(cls.status).all()

        return {
            'total': total,
            'by_severity': {s: c for s, c in severity_counts},
            'by_status': {s: c for s, c in status_counts},
        }
