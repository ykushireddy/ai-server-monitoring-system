"""
Alert management service.
Creates, manages, and escalates alerts based on anomalies and thresholds.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import current_app

from models.alert import Alert, AlertSeverity, AlertStatus
from models.log import Log, EventType

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manages alert lifecycle: creation, acknowledgment, resolution.
    
    Integrates with EmailService for notifications.
    """
    
    # Cooldown period to prevent alert flooding (seconds)
    ALERT_COOLDOWN = 300  # 5 minutes
    
    def __init__(self, email_service=None):
        """
        Initialize alert manager.
        
        Args:
            email_service: Optional EmailService instance for notifications
        """
        self.email_service = email_service
        self._recent_alerts = {}  # Track recent alerts for deduplication
    
    def _get_thresholds(self) -> Dict:
        """Get alert thresholds from configuration."""
        try:
            return {
                'cpu': {
                    'warning': current_app.config.get('CPU_WARNING_THRESHOLD', 70.0),
                    'critical': current_app.config.get('CPU_CRITICAL_THRESHOLD', 90.0)
                },
                'memory': {
                    'warning': current_app.config.get('MEMORY_WARNING_THRESHOLD', 75.0),
                    'critical': current_app.config.get('MEMORY_CRITICAL_THRESHOLD', 90.0)
                },
                'disk': {
                    'warning': current_app.config.get('DISK_WARNING_THRESHOLD', 80.0),
                    'critical': current_app.config.get('DISK_CRITICAL_THRESHOLD', 95.0)
                }
            }
        except RuntimeError:
            # Outside application context, use defaults
            return {
                'cpu': {'warning': 70.0, 'critical': 90.0},
                'memory': {'warning': 75.0, 'critical': 90.0},
                'disk': {'warning': 80.0, 'critical': 95.0}
            }
    
    def _should_create_alert(self, metric_name: str, severity: str) -> bool:
        """
        Check if we should create an alert (deduplication).
        
        Prevents creating duplicate alerts within cooldown period.
        """
        key = f"{metric_name}:{severity}"
        now = datetime.utcnow()
        
        if key in self._recent_alerts:
            last_alert_time = self._recent_alerts[key]
            if (now - last_alert_time).total_seconds() < self.ALERT_COOLDOWN:
                return False
        
        self._recent_alerts[key] = now
        return True
    
    def check_thresholds(self, metric, db_session) -> List[Alert]:
        """
        Check metric values against thresholds and create alerts.
        
        Args:
            metric: Metric object or dictionary
            db_session: SQLAlchemy database session
            
        Returns:
            List of created Alert objects
        """
        if hasattr(metric, 'to_dict'):
            metric = metric.to_dict()
        
        thresholds = self._get_thresholds()
        alerts = []
        
        # Check CPU
        cpu = metric.get('cpu_usage', 0) or 0
        if cpu >= thresholds['cpu']['critical']:
            alert = self._create_alert_if_needed(
                'cpu', cpu, AlertSeverity.CRITICAL,
                f"Critical CPU usage detected: {cpu:.1f}% exceeds threshold of "
                f"{thresholds['cpu']['critical']:.0f}%",
                db_session
            )
            if alert:
                alerts.append(alert)
        elif cpu >= thresholds['cpu']['warning']:
            alert = self._create_alert_if_needed(
                'cpu', cpu, AlertSeverity.WARNING,
                f"High CPU usage warning: {cpu:.1f}% exceeds threshold of "
                f"{thresholds['cpu']['warning']:.0f}%",
                db_session
            )
            if alert:
                alerts.append(alert)
        
        # Check Memory
        memory = metric.get('memory_usage', 0) or 0
        if memory >= thresholds['memory']['critical']:
            alert = self._create_alert_if_needed(
                'memory', memory, AlertSeverity.CRITICAL,
                f"Critical memory usage detected: {memory:.1f}% exceeds threshold of "
                f"{thresholds['memory']['critical']:.0f}%",
                db_session
            )
            if alert:
                alerts.append(alert)
        elif memory >= thresholds['memory']['warning']:
            alert = self._create_alert_if_needed(
                'memory', memory, AlertSeverity.WARNING,
                f"High memory usage warning: {memory:.1f}% exceeds threshold of "
                f"{thresholds['memory']['warning']:.0f}%",
                db_session
            )
            if alert:
                alerts.append(alert)
        
        # Check Disk
        disk = metric.get('disk_usage', 0) or 0
        if disk >= thresholds['disk']['critical']:
            alert = self._create_alert_if_needed(
                'disk', disk, AlertSeverity.CRITICAL,
                f"Critical disk usage detected: {disk:.1f}% exceeds threshold of "
                f"{thresholds['disk']['critical']:.0f}%",
                db_session
            )
            if alert:
                alerts.append(alert)
        elif disk >= thresholds['disk']['warning']:
            alert = self._create_alert_if_needed(
                'disk', disk, AlertSeverity.WARNING,
                f"High disk usage warning: {disk:.1f}% exceeds threshold of "
                f"{thresholds['disk']['warning']:.0f}%",
                db_session
            )
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def _create_alert_if_needed(
        self,
        metric_name: str,
        metric_value: float,
        severity: AlertSeverity,
        message: str,
        db_session,
        anomaly_score: float = None
    ) -> Optional[Alert]:
        """
        Create an alert if not in cooldown period.
        
        Args:
            metric_name: Name of the metric (cpu, memory, disk, network)
            metric_value: Current value of the metric
            severity: Alert severity level
            message: Human-readable alert message
            db_session: SQLAlchemy database session
            anomaly_score: Optional ML anomaly score
            
        Returns:
            Created Alert object or None if in cooldown
        """
        severity_value = severity.value if isinstance(severity, AlertSeverity) else severity
        
        if not self._should_create_alert(metric_name, severity_value):
            logger.debug(f"Skipping duplicate alert: {metric_name} {severity_value}")
            return None
        
        return self.create_alert(
            metric_name, metric_value, severity_value, message,
            db_session, anomaly_score
        )
    
    def create_alert(
        self,
        metric_name: str,
        metric_value: float,
        severity: str,
        message: str,
        db_session,
        anomaly_score: float = None
    ) -> Alert:
        """
        Create and store a new alert.
        
        Args:
            metric_name: Name of the metric
            metric_value: Current value
            severity: Severity level string
            message: Alert message
            db_session: SQLAlchemy database session
            anomaly_score: Optional anomaly score
            
        Returns:
            Created Alert object
        """
        try:
            alert = Alert(
                metric_name=metric_name,
                metric_value=metric_value,
                severity=severity,
                message=message,
                status=AlertStatus.ACTIVE.value,
                anomaly_score=anomaly_score
            )
            
            db_session.add(alert)
            db_session.commit()
            
            # Log the alert creation
            Log.create(
                EventType.ALERT_CREATED,
                f"Alert created: [{severity.upper()}] {metric_name}={metric_value:.1f}",
                details={
                    'alert_id': alert.id,
                    'metric_name': metric_name,
                    'metric_value': metric_value,
                    'severity': severity
                },
                severity='warning' if severity == 'warning' else 'error',
                source='AlertManager'
            )
            
            # Send notification
            if self.email_service:
                self._send_notification(alert)
            
            logger.info(f"Created alert {alert.id}: [{severity}] {metric_name}={metric_value:.1f}")
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            db_session.rollback()
            raise
    
    def create_anomaly_alert(self, anomaly, db_session) -> Optional[Alert]:
        """
        Create an alert from an anomaly detection result.
        
        Args:
            anomaly: Anomaly object
            db_session: SQLAlchemy database session
            
        Returns:
            Created Alert object or None if not anomalous
        """
        if not anomaly.is_anomaly:
            return None
        
        severity_map = {
            'warning': AlertSeverity.WARNING,
            'critical': AlertSeverity.CRITICAL,
            'normal': AlertSeverity.INFO
        }
        
        severity = severity_map.get(anomaly.severity, AlertSeverity.WARNING)
        
        message = (
            f"Anomaly detected by ML model: {anomaly.metric_name} at {anomaly.metric_value:.1f}%. "
            f"Anomaly score: {anomaly.anomaly_score:.4f}"
        )
        
        return self._create_alert_if_needed(
            f"anomaly_{anomaly.metric_name}",
            anomaly.metric_value,
            severity,
            message,
            db_session,
            anomaly.anomaly_score
        )
    
    def _send_notification(self, alert: Alert):
        """Send email notification for an alert."""
        if not self.email_service:
            return
        
        try:
            subject = f"[{alert.severity.upper()}] Server Alert: {alert.metric_name}"
            
            body = f"""
Server Monitoring Alert

Severity: {alert.severity.upper()}
Metric: {alert.metric_name}
Value: {alert.metric_value:.2f}
Timestamp: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC

Description:
{alert.message}

{'Anomaly Score: ' + str(round(alert.anomaly_score, 4)) if alert.anomaly_score else ''}

This is an automated message from the Server Monitoring System.
            """.strip()
            
            self.email_service.send_alert_email(subject, body, alert)
            
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")
    
    def acknowledge_alert(self, alert_id: int, db_session) -> Optional[Alert]:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            db_session: SQLAlchemy database session
            
        Returns:
            Updated Alert object or None
        """
        try:
            alert = db_session.get(Alert, alert_id)
            if not alert:
                return None
            
            alert.status = AlertStatus.ACKNOWLEDGED.value
            alert.acknowledged_at = datetime.utcnow()
            db_session.commit()
            
            Log.create(
                EventType.ALERT_ACKNOWLEDGED,
                f"Alert {alert_id} acknowledged",
                details={'alert_id': alert_id},
                severity='info',
                source='AlertManager'
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            db_session.rollback()
            return None
    
    def resolve_alert(self, alert_id: int, db_session) -> Optional[Alert]:
        """
        Resolve an alert.
        
        Args:
            alert_id: ID of the alert to resolve
            db_session: SQLAlchemy database session
            
        Returns:
            Updated Alert object or None
        """
        try:
            alert = db_session.get(Alert, alert_id)
            if not alert:
                return None
            
            alert.status = AlertStatus.RESOLVED.value
            alert.resolved_at = datetime.utcnow()
            db_session.commit()
            
            Log.create(
                EventType.ALERT_RESOLVED,
                f"Alert {alert_id} resolved",
                details={'alert_id': alert_id},
                severity='info',
                source='AlertManager'
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            db_session.rollback()
            return None
    
    def auto_resolve_alerts(self, metric, db_session) -> List[Alert]:
        """
        Auto-resolve alerts when metrics return to normal.
        
        Args:
            metric: Current metric values
            db_session: SQLAlchemy database session
            
        Returns:
            List of auto-resolved alerts
        """
        if hasattr(metric, 'to_dict'):
            metric = metric.to_dict()
        
        thresholds = self._get_thresholds()
        resolved = []
        
        # Get active alerts
        active_alerts = db_session.query(Alert).filter(
            Alert.status == AlertStatus.ACTIVE.value
        ).all()
        
        for alert in active_alerts:
            should_resolve = False
            
            # Check if the metric is back below warning threshold
            if alert.metric_name == 'cpu':
                if metric.get('cpu_usage', 100) < thresholds['cpu']['warning']:
                    should_resolve = True
            elif alert.metric_name == 'memory':
                if metric.get('memory_usage', 100) < thresholds['memory']['warning']:
                    should_resolve = True
            elif alert.metric_name == 'disk':
                if metric.get('disk_usage', 100) < thresholds['disk']['warning']:
                    should_resolve = True
            
            if should_resolve:
                resolved_alert = self.resolve_alert(alert.id, db_session)
                if resolved_alert:
                    resolved.append(resolved_alert)
                    logger.info(f"Auto-resolved alert {alert.id}: {alert.metric_name} returned to normal")
        
        return resolved
