"""
Seed the database with sample metrics, alerts, anomalies, and logs.
Run: python seed_data.py
"""

import random
from datetime import datetime, timedelta

from app import app
from models.metric import db, Metric
from models.alert import Alert, AlertSeverity, AlertStatus
from models.anomaly import Anomaly
from models.log import Log, EventType


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        now = datetime.utcnow()
        metrics = []

        for i in range(120):
            ts = now - timedelta(minutes=(120 - i) * 2)
            cpu = random.uniform(15, 85)
            mem = random.uniform(30, 80)
            disk = random.uniform(40, 75)
            health = Metric.calculate_health_score(cpu, mem, disk)
            m = Metric(
                cpu_usage=cpu,
                memory_usage=mem,
                disk_usage=disk,
                network_sent=random.uniform(1e6, 5e6),
                network_received=random.uniform(1e6, 5e6),
                network_sent_rate=random.uniform(1000, 50000),
                network_received_rate=random.uniform(1000, 80000),
                process_count=random.randint(80, 200),
                uptime_seconds=86400 * 3 + i * 120,
                health_score=health,
                created_at=ts,
            )
            metrics.append(m)
            db.session.add(m)

        db.session.commit()
        print(f'Seeded {len(metrics)} metrics')

        alert_samples = [
            ('cpu', 92.5, AlertSeverity.CRITICAL, 'Critical CPU usage detected'),
            ('memory', 78.2, AlertSeverity.WARNING, 'High memory usage warning'),
            ('disk', 81.0, AlertSeverity.WARNING, 'High disk usage warning'),
        ]
        for metric_name, value, severity, msg in alert_samples:
            db.session.add(
                Alert(
                    metric_name=metric_name,
                    metric_value=value,
                    severity=severity.value,
                    message=msg,
                    status=AlertStatus.ACTIVE.value,
                    created_at=now - timedelta(hours=1),
                )
            )

        db.session.add(
            Alert(
                metric_name='cpu',
                metric_value=65.0,
                severity=AlertSeverity.WARNING.value,
                message='Resolved CPU spike',
                status=AlertStatus.RESOLVED.value,
                created_at=now - timedelta(hours=6),
                resolved_at=now - timedelta(hours=5),
            )
        )
        db.session.commit()
        print('Seeded alerts')

        for _ in range(15):
            is_anom = random.random() < 0.2
            score = random.uniform(-0.5, 0.3) if is_anom else random.uniform(0.1, 0.5)
            db.session.add(
                Anomaly(
                    metric_name=random.choice(['cpu', 'memory', 'disk']),
                    metric_value=random.uniform(50, 95),
                    anomaly_score=score,
                    is_anomaly=is_anom,
                    severity=Anomaly.score_to_severity(score, is_anom),
                    created_at=now - timedelta(hours=random.randint(1, 12)),
                )
            )
        db.session.commit()
        print('Seeded anomalies')

        Log.create(EventType.SYSTEM_START, 'Database seeded', source='seed_data.py')
        Log.create(
            EventType.METRIC_COLLECTION,
            'Sample metrics loaded',
            details={'count': len(metrics)},
            source='seed_data.py',
        )
        print('Seeding complete.')


if __name__ == '__main__':
    seed()
