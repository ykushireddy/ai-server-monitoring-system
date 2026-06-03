"""
Email notification service.
Supports both real email sending and simulation mode for development.
"""

import logging
from datetime import datetime
from typing import List, Optional
from flask import current_app

from models.log import Log, EventType

logger = logging.getLogger(__name__)


class EmailService:
    """
    Handles email notifications for alerts.
    
    In simulation mode (default), logs emails instead of sending them.
    """
    
    def __init__(self, mail_instance=None):
        """
        Initialize email service.
        
        Args:
            mail_instance: Flask-Mail instance for real email sending
        """
        self.mail = mail_instance
        self._email_log = []  # In-memory log of simulated emails
    
    def _get_config(self, key, default=None):
        """Safely get configuration value."""
        try:
            return current_app.config.get(key, default)
        except RuntimeError:
            # Outside application context
            return default
    
    def send_alert_email(self, subject: str, body: str, alert=None) -> bool:
        """
        Send an alert email notification.
        
        Args:
            subject: Email subject line
            body: Email body text
            alert: Optional Alert object for context
            
        Returns:
            True if email was sent/simulated successfully
        """
        simulation_mode = self._get_config('MAIL_SIMULATION_MODE', True)
        recipients = self._get_config('MAIL_RECIPIENTS', ['admin@monitoring.local'])
        sender = self._get_config('MAIL_DEFAULT_SENDER', 'alerts@monitoring.local')
        
        if isinstance(recipients, str):
            recipients = [recipients]
        
        email_data = {
            'subject': subject,
            'body': body,
            'sender': sender,
            'recipients': recipients,
            'timestamp': datetime.utcnow().isoformat(),
            'alert_id': alert.id if alert else None
        }
        
        if simulation_mode:
            return self._simulate_email(email_data)
        else:
            return self._send_real_email(email_data)
    
    def _simulate_email(self, email_data: dict) -> bool:
        """
        Simulate sending an email (for development/testing).
        
        Logs the email to database and in-memory store.
        """
        try:
            # Store in memory for API access
            self._email_log.append(email_data)
            
            # Trim in-memory log to last 100 emails
            if len(self._email_log) > 100:
                self._email_log = self._email_log[-100:]
            
            # Log to database
            Log.create(
                EventType.EMAIL_SENT,
                f"[SIMULATED] Email sent: {email_data['subject']}",
                details={
                    'subject': email_data['subject'],
                    'recipients': email_data['recipients'],
                    'simulation': True,
                    'alert_id': email_data.get('alert_id')
                },
                severity='info',
                source='EmailService'
            )
            
            logger.info(f"[SIMULATED EMAIL]\n"
                       f"  To: {', '.join(email_data['recipients'])}\n"
                       f"  Subject: {email_data['subject']}\n"
                       f"  Body preview: {email_data['body'][:100]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to simulate email: {e}")
            return False
    
    def _send_real_email(self, email_data: dict) -> bool:
        """
        Send a real email using Flask-Mail.
        """
        if not self.mail:
            logger.error("Flask-Mail not configured")
            return self._simulate_email(email_data)
        
        try:
            from flask_mail import Message
            
            msg = Message(
                subject=email_data['subject'],
                sender=email_data['sender'],
                recipients=email_data['recipients'],
                body=email_data['body']
            )
            
            self.mail.send(msg)
            
            # Log success
            Log.create(
                EventType.EMAIL_SENT,
                f"Email sent: {email_data['subject']}",
                details={
                    'subject': email_data['subject'],
                    'recipients': email_data['recipients'],
                    'alert_id': email_data.get('alert_id')
                },
                severity='info',
                source='EmailService'
            )
            
            logger.info(f"Email sent to {', '.join(email_data['recipients'])}: {email_data['subject']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            
            # Log failure
            Log.create(
                EventType.EMAIL_FAILED,
                f"Email failed: {email_data['subject']} - {str(e)}",
                details={
                    'subject': email_data['subject'],
                    'recipients': email_data['recipients'],
                    'error': str(e),
                    'alert_id': email_data.get('alert_id')
                },
                severity='error',
                source='EmailService'
            )
            
            return False
    
    def get_simulated_emails(self, limit: int = 50) -> List[dict]:
        """
        Get recent simulated emails.
        
        Args:
            limit: Maximum number of emails to return
            
        Returns:
            List of email data dictionaries (most recent first)
        """
        return list(reversed(self._email_log[-limit:]))
    
    def send_daily_summary(self, metrics_stats: dict, alert_stats: dict) -> bool:
        """
        Send daily summary email.
        
        Args:
            metrics_stats: Metrics statistics dictionary
            alert_stats: Alert statistics dictionary
            
        Returns:
            True if email sent successfully
        """
        subject = f"Daily Server Monitoring Summary - {datetime.utcnow().strftime('%Y-%m-%d')}"
        
        body = f"""
Daily Server Monitoring Summary
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

=== METRICS SUMMARY (Last 24 Hours) ===

CPU Usage:
  Average: {metrics_stats.get('cpu', {}).get('avg', 'N/A')}%
  Maximum: {metrics_stats.get('cpu', {}).get('max', 'N/A')}%
  Minimum: {metrics_stats.get('cpu', {}).get('min', 'N/A')}%

Memory Usage:
  Average: {metrics_stats.get('memory', {}).get('avg', 'N/A')}%
  Maximum: {metrics_stats.get('memory', {}).get('max', 'N/A')}%
  Minimum: {metrics_stats.get('memory', {}).get('min', 'N/A')}%

Disk Usage:
  Average: {metrics_stats.get('disk', {}).get('avg', 'N/A')}%
  Maximum: {metrics_stats.get('disk', {}).get('max', 'N/A')}%
  Minimum: {metrics_stats.get('disk', {}).get('min', 'N/A')}%

Overall Health Score: {metrics_stats.get('health_avg', 'N/A')}

=== ALERT SUMMARY ===

Total Alerts: {alert_stats.get('total', 0)}

By Severity:
  Critical: {alert_stats.get('by_severity', {}).get('critical', 0)}
  Warning: {alert_stats.get('by_severity', {}).get('warning', 0)}
  Info: {alert_stats.get('by_severity', {}).get('info', 0)}

By Status:
  Active: {alert_stats.get('by_status', {}).get('active', 0)}
  Acknowledged: {alert_stats.get('by_status', {}).get('acknowledged', 0)}
  Resolved: {alert_stats.get('by_status', {}).get('resolved', 0)}

---
This is an automated daily summary from the Server Monitoring System.
        """.strip()
        
        return self.send_alert_email(subject, body)
