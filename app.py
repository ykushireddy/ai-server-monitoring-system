"""

AI-Powered Server Monitoring and Alert System



Main application entry point.

"""



import os

import logging

from logging.handlers import RotatingFileHandler

from datetime import datetime, timedelta



from flask import Flask

from flask_cors import CORS

from apscheduler.schedulers.background import BackgroundScheduler

from sqlalchemy import text



from config import get_config

from extensions import mail, login_manager

from models.metric import db, Metric

from models.alert import Alert

from models.anomaly import Anomaly

from models.log import Log, EventType



from routes.dashboard import dashboard_bp

from routes.metrics import metrics_bp

from routes.alerts import alerts_bp

from routes.logs import logs_bp

from routes.reports import reports_bp

from routes.health import health_bp

from routes.auth import auth_bp



from services.collector import MetricsCollector

from services.anomaly_detector import AnomalyDetector

from services.alert_manager import AlertManager

from services.email_service import EmailService





def setup_logging(app):

    """Configure application and file logging."""

    log_dir = app.config.get('LOG_DIR', 'logs')

    os.makedirs(log_dir, exist_ok=True)



    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)

    app.logger.setLevel(log_level)



    if not app.debug and not app.testing:

        file_handler = RotatingFileHandler(

            app.config.get('LOG_FILE', os.path.join(log_dir, 'monitoring.log')),

            maxBytes=app.config.get('LOG_MAX_BYTES', 10485760),

            backupCount=app.config.get('LOG_BACKUP_COUNT', 5),

        )

        file_handler.setFormatter(logging.Formatter(app.config.get('LOG_FORMAT')))

        file_handler.setLevel(log_level)

        app.logger.addHandler(file_handler)





def create_app(config_class=None):

    """Application factory."""

    app = Flask(__name__)



    if config_class is None:

        config_class = get_config()

    app.config.from_object(config_class)



    os.makedirs(app.config.get('LOG_DIR', 'logs'), exist_ok=True)

    os.makedirs(app.config.get('REPORTS_DIR', 'reports'), exist_ok=True)

    os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)

    os.makedirs(os.path.join(os.path.dirname(__file__), 'ml_artifacts'), exist_ok=True)



    setup_logging(app)



    db.init_app(app)

    mail.init_app(app)

    login_manager.init_app(app)



    CORS(app, supports_credentials=True)



    app.register_blueprint(health_bp)

    app.register_blueprint(auth_bp)

    app.register_blueprint(dashboard_bp)

    app.register_blueprint(metrics_bp)

    app.register_blueprint(alerts_bp)

    app.register_blueprint(logs_bp)

    app.register_blueprint(reports_bp)



    with app.app_context():

        db.create_all()

        app.logger.info('Database initialized')



    app.metrics_collector = MetricsCollector()

    app.anomaly_detector = AnomalyDetector(

        contamination=app.config.get('ML_CONTAMINATION', 0.05),

        min_samples=app.config.get('ML_MIN_SAMPLES', 100),

    )

    app.email_service = EmailService(mail_instance=mail)

    app.alert_manager = AlertManager(email_service=app.email_service)



    def startup_ml_training():

        """Train Isolation Forest at startup when enough metrics exist in the database."""

        min_samples = app.config.get('ML_MIN_SAMPLES', 100)

        if app.anomaly_detector.is_trained:

            app.logger.info(

                'Startup ML training skipped: model already loaded from %s',

                app.anomaly_detector.MODEL_DIR,

            )

            return



        metrics = Metric.get_history(hours=168, limit=5000)

        if len(metrics) < min_samples:

            app.logger.info(

                'Startup ML training skipped: %s/%s metrics in database',

                len(metrics),

                min_samples,

            )

            return



        if not app.anomaly_detector.train(metrics):

            app.logger.warning('Startup ML training failed')

            return



        model_path = app.anomaly_detector.MODEL_PATH

        scaler_path = app.anomaly_detector.SCALER_PATH

        if os.path.isfile(model_path) and os.path.isfile(scaler_path):

            app.logger.info(

                'Startup ML training succeeded on %s samples; saved %s and %s',

                len(metrics),

                model_path,

                scaler_path,

            )

            Log.create(

                EventType.ML_TRAINING,

                f'Startup ML training completed on {len(metrics)} samples',

                details={

                    'sample_count': len(metrics),

                    'model_path': model_path,

                    'scaler_path': scaler_path,

                },

                severity='info',

                source='AnomalyDetector',

            )

        else:

            app.logger.error(

                'Startup ML training reported success but artifacts missing: %s, %s',

                model_path,

                scaler_path,

            )



    def monitoring_job():

        with app.app_context():

            try:

                metric = app.metrics_collector.collect_and_store(db.session)

                if metric:

                    anomaly = app.anomaly_detector.detect_and_store(metric, db.session)

                    app.alert_manager.check_thresholds(metric, db.session)

                    if anomaly and anomaly.is_anomaly:

                        app.alert_manager.create_anomaly_alert(anomaly, db.session)

                    app.alert_manager.auto_resolve_alerts(metric, db.session)

            except Exception as e:

                app.logger.error('Monitoring job error: %s', e)



    def ml_retrain_job():

        with app.app_context():

            try:

                min_samples = app.config.get('ML_MIN_SAMPLES', 100)

                metrics = Metric.get_history(hours=168, limit=5000)

                if len(metrics) >= min_samples:

                    if app.anomaly_detector.train(metrics):

                        Log.create(

                            EventType.ML_TRAINING,

                            f'ML model retrained on {len(metrics)} samples',

                            details={'sample_count': len(metrics)},

                            severity='info',

                            source='AnomalyDetector',

                        )

            except Exception as e:

                app.logger.error('ML retrain job error: %s', e)



    def retention_cleanup_job():

        with app.app_context():

            try:

                days = app.config.get('METRICS_RETENTION_DAYS', 30)

                cutoff = datetime.utcnow() - timedelta(days=days)

                deleted = {

                    'metrics': Metric.query.filter(Metric.created_at < cutoff).delete(),

                    'alerts': Alert.query.filter(Alert.created_at < cutoff).delete(),

                    'anomalies': Anomaly.query.filter(Anomaly.created_at < cutoff).delete(),

                    'logs': Log.query.filter(Log.created_at < cutoff).delete(),

                }

                db.session.commit()

                total = sum(deleted.values())

                if total > 0:

                    app.logger.info(

                        'Retention cleanup removed %s records older than %s days',

                        total,

                        days,

                    )

                    Log.create(

                        EventType.CONFIG_CHANGE,

                        f'Retention cleanup: removed {total} records',

                        details={'days': days, 'deleted': deleted},

                        severity='info',

                        source='retention_cleanup',

                    )

            except Exception as e:

                db.session.rollback()

                app.logger.error('Retention cleanup error: %s', e)



    scheduler = BackgroundScheduler(daemon=True)

    interval = app.config.get('MONITORING_INTERVAL', 5)

    scheduler.add_job(monitoring_job, 'interval', seconds=interval, id='monitoring')

    scheduler.add_job(

        ml_retrain_job,

        'interval',

        seconds=app.config.get('ML_RETRAIN_INTERVAL', 3600),

        id='ml_retrain',

    )

    scheduler.add_job(

        retention_cleanup_job,

        'interval',

        hours=24,

        id='retention_cleanup',

    )

    scheduler.start()

    app.scheduler = scheduler



    with app.app_context():

        startup_ml_training()



    with app.app_context():

        Log.create(

            EventType.SYSTEM_START,

            'Server monitoring system started',

            details={'monitoring_interval': interval},

            severity='info',

            source='app',

        )



    return app





app = create_app()





if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))

    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))


