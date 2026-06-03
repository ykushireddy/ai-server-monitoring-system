"""
Logs routes — audit trail UI and API.
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, render_template, current_app

from models.metric import db
from models.log import Log, EventType

logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/logs')
def logs_page():
    """Render the application logs page."""
    return render_template('logs.html')


@logs_bp.route('/api/logs')
def get_logs():
    """
    Get logs with filtering and pagination.

    Query params: event_type, severity, hours, page, per_page, q (search)
    """
    try:
        event_type = request.args.get('event_type')
        severity = request.args.get('severity')
        search = request.args.get('q')
        hours = request.args.get('hours', 24, type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)

        hours = max(1, min(hours, 720))
        page = max(1, page)
        per_page = max(1, min(per_page, 100))

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = Log.query.filter(Log.created_at >= cutoff)

        if event_type:
            query = query.filter(Log.event_type == event_type)
        if severity:
            query = query.filter(Log.severity == severity)
        if search:
            query = query.filter(Log.description.ilike(f'%{search}%'))

        query = query.order_by(Log.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'data': [entry.to_dict() for entry in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
            },
            'event_types': [e.value for e in EventType],
        })

    except Exception as e:
        current_app.logger.error('Error getting logs: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@logs_bp.route('/api/logs/statistics')
def log_statistics():
    """Get log statistics for the selected time window."""
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = max(1, min(hours, 720))
        stats = Log.get_statistics(hours=hours)
        return jsonify({'success': True, 'data': stats, 'hours': hours})
    except Exception as e:
        current_app.logger.error('Error getting log statistics: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500
