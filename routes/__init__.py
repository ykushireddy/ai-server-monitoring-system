"""
Routes package.
Contains Flask blueprints for all application endpoints.
"""

from routes.dashboard import dashboard_bp
from routes.metrics import metrics_bp
from routes.alerts import alerts_bp
from routes.logs import logs_bp
from routes.reports import reports_bp
from routes.health import health_bp
from routes.auth import auth_bp

__all__ = [
    'dashboard_bp',
    'metrics_bp',
    'alerts_bp',
    'logs_bp',
    'reports_bp',
    'health_bp',
    'auth_bp',
]
