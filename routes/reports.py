"""
Reports API routes.
Provides endpoints for generating and downloading reports.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request, render_template, current_app, Response
from flask_login import login_required
from models.metric import Metric
from models.alert import Alert
from models.anomaly import Anomaly
from models.log import Log, EventType
from services.report_service import ReportService

reports_bp = Blueprint('reports', __name__)

# Initialize report service
report_service = ReportService()


@reports_bp.route('/reports')
def reports_page():
    """Render the reports page."""
    return render_template('reports.html')


@reports_bp.route('/api/reports/csv')
@login_required
def generate_csv():
    """
    Generate and download CSV report.
    
    Query Parameters:
        hours: Time window for report (default: 24)
        
    Returns:
        CSV file download
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = max(1, min(hours, 168))
        
        # Gather data
        metrics = Metric.get_history(hours=hours, limit=10000)
        alerts = Alert.get_recent_alerts(hours=hours, limit=1000)
        anomalies = Anomaly.get_recent_anomalies(hours=hours, only_anomalies=False)
        
        # Generate CSV
        csv_content = report_service.generate_csv_report(
            metrics, alerts, anomalies, hours
        )
        
        # Log report generation
        Log.create(
            EventType.REPORT_GENERATED,
            f"CSV report generated for last {hours} hours",
            details={'hours': hours, 'format': 'csv'},
            source='ReportService'
        )
        
        # Create response
        filename = f"monitoring_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating CSV report: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@reports_bp.route('/api/reports/pdf')
@login_required
def generate_pdf():
    """
    Generate and download PDF report.
    
    Query Parameters:
        hours: Time window for report (default: 24)
        
    Returns:
        PDF file download
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = max(1, min(hours, 168))
        
        # Gather statistics
        metrics_stats = Metric.get_statistics(hours=hours) or {}
        alert_stats = Alert.get_statistics(hours=hours) or {}
        anomaly_stats = Anomaly.get_statistics(hours=hours) or {}
        
        # Generate PDF
        pdf_content = report_service.generate_pdf_report(
            metrics_stats, alert_stats, anomaly_stats, hours
        )
        
        # Log report generation
        Log.create(
            EventType.REPORT_GENERATED,
            f"PDF report generated for last {hours} hours",
            details={'hours': hours, 'format': 'pdf'},
            source='ReportService'
        )
        
        # Create response
        filename = f"monitoring_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return Response(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating PDF report: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@reports_bp.route('/api/reports/summary')
def get_report_summary():
    """
    Get a summary of available report data.
    
    Returns:
        JSON with data availability and statistics
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = max(1, min(hours, 168))
        
        metrics_stats = Metric.get_statistics(hours=hours)
        alert_stats = Alert.get_statistics(hours=hours)
        anomaly_stats = Anomaly.get_statistics(hours=hours)
        log_stats = Log.get_statistics(hours=hours)
        
        return jsonify({
            'success': True,
            'data': {
                'hours': hours,
                'metrics': metrics_stats,
                'alerts': alert_stats,
                'anomalies': anomaly_stats,
                'logs': log_stats,
                'generated_at': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting report summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
