"""
Health check endpoint for load balancers and orchestrators.
"""

from datetime import datetime

from flask import Blueprint, jsonify, current_app
from sqlalchemy import text

from models.metric import db

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health_check():
    """Return application, database, and scheduler status."""
    db_connected = False
    db_error = None
    try:
        db.session.execute(text('SELECT 1'))
        db_connected = True
    except Exception as exc:
        db_error = str(exc)

    scheduler = getattr(current_app, 'scheduler', None)
    scheduler_running = bool(scheduler and scheduler.running)
    job_ids = []
    if scheduler_running:
        try:
            job_ids = [job.id for job in scheduler.get_jobs()]
        except Exception:
            job_ids = []

    application_ok = True
    overall_healthy = db_connected and scheduler_running
    status = 'healthy' if overall_healthy else 'degraded'
    http_status = 200 if overall_healthy else 503

    return jsonify({
        'status': status,
        'timestamp': datetime.utcnow().isoformat(),
        'application': {
            'ok': application_ok,
            'debug': current_app.config.get('DEBUG', False),
            'environment': current_app.config.get('ENV', 'production'),
        },
        'database': {
            'connected': db_connected,
            'error': db_error,
        },
        'scheduler': {
            'running': scheduler_running,
            'jobs': job_ids,
        },
    }), http_status
