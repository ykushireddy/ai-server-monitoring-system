"""
Anomaly model for storing machine learning detection results.
"""
from datetime import datetime
from models.metric import db
class Anomaly(db.Model):
    """
    Stores anomaly detection results from the Isolation Forest model.
    
    Attributes:
        id: Primary key
        metric_name: Name of the metric analyzed
        metric_value: The value that was analyzed
        anomaly_score: Score from Isolation Forest (-1 to 1, negative = anomaly)
        is_anomaly: Boolean indicating if this was classified as an anomaly
        severity: Computed severity based on anomaly score
        features_json: JSON string of all features used in detection
        created_at: When the anomaly was detected
    """
    
    __tablename__ = 'anomalies'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    metric_name = db.Column(db.String(50), nullable=False, index=True)
    metric_value = db.Column(db.Float, nullable=False)
    anomaly_score = db.Column(db.Float, nullable=False)
    is_anomaly = db.Column(db.Boolean, nullable=False, default=False, index=True)
    severity = db.Column(db.String(20), nullable=False, default='normal')
    features_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Anomaly {self.id} {self.metric_name}={self.metric_value} score={self.anomaly_score}>"
    
    def to_dict(self):
        """Convert anomaly to dictionary for JSON serialization."""
        import json
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': round(self.metric_value, 2),
            'anomaly_score': round(self.anomaly_score, 4),
            'is_anomaly': self.is_anomaly,
            'severity': self.severity,
            'features': json.loads(self.features_json) if self.features_json else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def score_to_severity(anomaly_score, is_anomaly):
        """
        Convert anomaly score to severity level.
        
        Isolation Forest scores:
        - Positive scores (close to 1): normal
        - Negative scores (close to -1): anomaly
        - Score around 0: borderline
        
        Args:
            anomaly_score: Raw score from Isolation Forest
            is_anomaly: Boolean from model prediction
            
        Returns:
            Severity string: 'normal', 'warning', or 'critical'
        """
        if not is_anomaly:
            return 'normal'
        
        # More negative = more anomalous
        if anomaly_score < -0.3:
            return 'critical'
        elif anomaly_score < 0:
            return 'warning'
        else:
            return 'normal'
    
    @classmethod
    def get_recent_anomalies(cls, hours=24, only_anomalies=True):
        """Get recent anomaly records."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        query = cls.query.filter(cls.created_at >= cutoff)
        if only_anomalies:
            query = query.filter(cls.is_anomaly == True)
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_anomaly_count(cls, hours=24):
        """Get count of anomalies in the specified period."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return cls.query.filter(
            cls.created_at >= cutoff,
            cls.is_anomaly == True
        ).count()
    
    @classmethod
    def get_statistics(cls, hours=24):
        """Get anomaly detection statistics."""
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        total = cls.query.filter(cls.created_at >= cutoff).count()
        anomalies = cls.query.filter(
            cls.created_at >= cutoff,
            cls.is_anomaly == True
        ).count()
        
        severity_counts = db.session.query(
            cls.severity,
            func.count(cls.id)
        ).filter(
            cls.created_at >= cutoff,
            cls.is_anomaly == True
        ).group_by(cls.severity).all()
        
        metric_counts = db.session.query(
            cls.metric_name,
            func.count(cls.id)
        ).filter(
            cls.created_at >= cutoff,
            cls.is_anomaly == True
        ).group_by(cls.metric_name).all()
        
        return {
            'total_analyzed': total,
            'total_anomalies': anomalies,
            'anomaly_rate': round((anomalies / total * 100) if total > 0 else 0, 2),
            'by_severity': {s: c for s, c in severity_counts},
            'by_metric': {m: c for m, c in metric_counts}
        }