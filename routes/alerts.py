"""
Alerts API routes.
Provides endpoints for alert management.
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required
from models.metric import db
from models.alert import Alert, AlertSeverity, AlertStatus

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('/alerts')
def alerts_page():
    """Render the alerts management page."""
    return render_template('alerts.html')


@alerts_bp.route('/api/alerts')
def get_alerts():
    """
    Get alerts with filtering and pagination.
    
    Query Parameters:
        severity: Filter by severity (critical/warning/info)
        status: Filter by status (active/acknowledged/resolved)
        metric: Filter by metric name
        hours: Time window in hours (default: 24)
        page: Page number (default: 1)
        per_page: Items per page (default: 25)
        
    Returns:
        JSON with alerts array and pagination info
    """
    try:
        # Parse parameters
        severity = request.args.get('severity')
        status = request.args.get('status')
        metric = request.args.get('metric')
        hours = request.args.get('hours', 24, type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        
        # Validate
        hours = max(1, min(hours, 720))  # Up to 30 days
        page = max(1, page)
        per_page = max(1, min(per_page, 100))
        
        # Build query
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = Alert.query.filter(Alert.created_at >= cutoff)
        
        if severity:
            query = query.filter(Alert.severity == severity)
        if status:
            query = query.filter(Alert.status == status)
        if metric:
            query = query.filter(Alert.metric_name.ilike(f'%{metric}%'))
        
        # Order by most recent first
        query = query.order_by(Alert.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': [a.to_dict() for a in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/api/alerts/<int:alert_id>')
def get_alert(alert_id):
    """Get a specific alert by ID."""
    try:
        alert = db.session.get(Alert, alert_id)
        
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': alert.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert."""
    try:
        alert = db.session.get(Alert, alert_id)
        
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
        
        alert.acknowledge()
        
        return jsonify({
            'success': True,
            'data': alert.to_dict(),
            'message': 'Alert acknowledged'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error acknowledging alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """Resolve an alert."""
    try:
        alert = db.session.get(Alert, alert_id)
        
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
        
        alert.resolve()
        
        return jsonify({
            'success': True,
            'data': alert.to_dict(),
            'message': 'Alert resolved'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error resolving alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/api/alerts/active')
def get_active_alerts():
    """Get all active (unresolved) alerts."""
    try:
        alerts = Alert.get_active_alerts()
        
        return jsonify({
            'success': True,
            'data': [a.to_dict() for a in alerts],
            'count': len(alerts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting active alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/api/alerts/statistics')
def get_alert_statistics():
    """Get alert statistics."""
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = max(1, min(hours, 720))
        
        stats = Alert.get_statistics(hours=hours)
        
        return jsonify({
            'success': True,
            'data': stats,
            'hours': hours
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting alert statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
