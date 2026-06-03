"""
Dashboard routes.
Serves the main dashboard page and dashboard data API.
"""

from flask import Blueprint, render_template, jsonify, current_app
from models.metric import Metric
from models.alert import Alert
from models.anomaly import Anomaly

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def index():
    """Render the main dashboard page."""
    return render_template('dashboard.html')


@dashboard_bp.route('/api/dashboard/summary')
def dashboard_summary():
    """
    Get dashboard summary data.
    
    Returns:
        JSON with current metrics, active alerts count, and health status
    """
    try:
        # Get latest metric
        latest_metric = Metric.get_latest()
        
        # Get active alert count
        active_alerts = Alert.get_active_count()
        
        # Get 24h statistics
        stats = Metric.get_statistics(hours=24)
        
        # Calculate system status
        status = 'healthy'
        if latest_metric:
            if (latest_metric.cpu_usage >= current_app.config.get('CPU_CRITICAL_THRESHOLD', 90) or
                latest_metric.memory_usage >= current_app.config.get('MEMORY_CRITICAL_THRESHOLD', 90) or
                latest_metric.disk_usage >= current_app.config.get('DISK_CRITICAL_THRESHOLD', 95)):
                status = 'critical'
            elif (latest_metric.cpu_usage >= current_app.config.get('CPU_WARNING_THRESHOLD', 70) or
                  latest_metric.memory_usage >= current_app.config.get('MEMORY_WARNING_THRESHOLD', 75) or
                  latest_metric.disk_usage >= current_app.config.get('DISK_WARNING_THRESHOLD', 80)):
                status = 'warning'
        
        # Format uptime
        from services.collector import MetricsCollector
        uptime_formatted = MetricsCollector.format_uptime(
            latest_metric.uptime_seconds if latest_metric else 0
        )
        
        return jsonify({
            'success': True,
            'data': {
                'current': latest_metric.to_dict() if latest_metric else None,
                'active_alerts': active_alerts,
                'system_status': status,
                'uptime_formatted': uptime_formatted,
                'statistics': stats,
                'thresholds': {
                    'cpu': {
                        'warning': current_app.config.get('CPU_WARNING_THRESHOLD', 70),
                        'critical': current_app.config.get('CPU_CRITICAL_THRESHOLD', 90)
                    },
                    'memory': {
                        'warning': current_app.config.get('MEMORY_WARNING_THRESHOLD', 75),
                        'critical': current_app.config.get('MEMORY_CRITICAL_THRESHOLD', 90)
                    },
                    'disk': {
                        'warning': current_app.config.get('DISK_WARNING_THRESHOLD', 80),
                        'critical': current_app.config.get('DISK_CRITICAL_THRESHOLD', 95)
                    }
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Dashboard summary error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/status')
def system_status():
    """
    Get current system status indicator.
    
    Returns:
        JSON with status (healthy/warning/critical) and details
    """
    try:
        latest = Metric.get_latest()
        active_alerts = Alert.get_active_alerts()
        
        # Determine status
        status = 'healthy'
        reasons = []
        
        if latest:
            thresholds = {
                'cpu': {
                    'warning': current_app.config.get('CPU_WARNING_THRESHOLD', 70),
                    'critical': current_app.config.get('CPU_CRITICAL_THRESHOLD', 90)
                },
                'memory': {
                    'warning': current_app.config.get('MEMORY_WARNING_THRESHOLD', 75),
                    'critical': current_app.config.get('MEMORY_CRITICAL_THRESHOLD', 90)
                },
                'disk': {
                    'warning': current_app.config.get('DISK_WARNING_THRESHOLD', 80),
                    'critical': current_app.config.get('DISK_CRITICAL_THRESHOLD', 95)
                }
            }
            
            # Check CPU
            if latest.cpu_usage >= thresholds['cpu']['critical']:
                status = 'critical'
                reasons.append(f"CPU at {latest.cpu_usage:.1f}%")
            elif latest.cpu_usage >= thresholds['cpu']['warning']:
                if status != 'critical':
                    status = 'warning'
                reasons.append(f"CPU at {latest.cpu_usage:.1f}%")
            
            # Check Memory
            if latest.memory_usage >= thresholds['memory']['critical']:
                status = 'critical'
                reasons.append(f"Memory at {latest.memory_usage:.1f}%")
            elif latest.memory_usage >= thresholds['memory']['warning']:
                if status != 'critical':
                    status = 'warning'
                reasons.append(f"Memory at {latest.memory_usage:.1f}%")
            
            # Check Disk
            if latest.disk_usage >= thresholds['disk']['critical']:
                status = 'critical'
                reasons.append(f"Disk at {latest.disk_usage:.1f}%")
            elif latest.disk_usage >= thresholds['disk']['warning']:
                if status != 'critical':
                    status = 'warning'
                reasons.append(f"Disk at {latest.disk_usage:.1f}%")
        
        # Check for critical alerts
        critical_alerts = [a for a in active_alerts if a.severity == 'critical']
        if critical_alerts:
            status = 'critical'
            reasons.append(f"{len(critical_alerts)} critical alert(s)")
        
        return jsonify({
            'success': True,
            'data': {
                'status': status,
                'reasons': reasons,
                'active_alerts_count': len(active_alerts),
                'last_updated': latest.created_at.isoformat() if latest else None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"System status error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
