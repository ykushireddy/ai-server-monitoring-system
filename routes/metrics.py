"""
Metrics API routes.
Provides endpoints for retrieving metric data and history.
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app
from models.metric import Metric
from services.collector import MetricsCollector

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


@metrics_bp.route('/latest')
def get_latest():
    """
    Get the most recent metric reading.
    
    Returns:
        JSON with latest metric data
    """
    try:
        metric = Metric.get_latest()
        
        if not metric:
            return jsonify({
                'success': True,
                'data': None,
                'message': 'No metrics available yet'
            })
        
        return jsonify({
            'success': True,
            'data': metric.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting latest metric: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/history')
def get_history():
    """
    Get metric history for charting.
    
    Query Parameters:
        hours: Number of hours to look back (default: 1)
        limit: Maximum number of records (default: 720)
        
    Returns:
        JSON with metrics array
    """
    try:
        hours = request.args.get('hours', 1, type=int)
        limit = request.args.get('limit', 720, type=int)
        
        # Validate parameters
        hours = max(1, min(hours, 168))  # 1 hour to 7 days
        limit = max(1, min(limit, 10000))
        
        metrics = Metric.get_history(hours=hours, limit=limit)
        
        return jsonify({
            'success': True,
            'data': [m.to_dict() for m in metrics],
            'count': len(metrics),
            'hours': hours
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting metric history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/network')
def get_network_metrics():
    """
    Get network-specific metrics.
    
    Query Parameters:
        hours: Number of hours to look back (default: 1)
        
    Returns:
        JSON with network metrics
    """
    try:
        hours = request.args.get('hours', 1, type=int)
        hours = max(1, min(hours, 168))
        
        metrics = Metric.get_history(hours=hours, limit=500)
        
        # Extract network data
        network_data = []
        for m in metrics:
            network_data.append({
                'timestamp': m.created_at.isoformat(),
                'sent_rate': round(m.network_sent_rate, 2),
                'received_rate': round(m.network_received_rate, 2),
                'sent_rate_formatted': MetricsCollector.format_bytes(m.network_sent_rate) + '/s',
                'received_rate_formatted': MetricsCollector.format_bytes(m.network_received_rate) + '/s'
            })
        
        # Calculate statistics
        if network_data:
            avg_sent = sum(d['sent_rate'] for d in network_data) / len(network_data)
            avg_recv = sum(d['received_rate'] for d in network_data) / len(network_data)
            max_sent = max(d['sent_rate'] for d in network_data)
            max_recv = max(d['received_rate'] for d in network_data)
        else:
            avg_sent = avg_recv = max_sent = max_recv = 0
        
        return jsonify({
            'success': True,
            'data': network_data,
            'statistics': {
                'avg_sent': round(avg_sent, 2),
                'avg_received': round(avg_recv, 2),
                'max_sent': round(max_sent, 2),
                'max_received': round(max_recv, 2),
                'avg_sent_formatted': MetricsCollector.format_bytes(avg_sent) + '/s',
                'avg_received_formatted': MetricsCollector.format_bytes(avg_recv) + '/s'
            },
            'count': len(network_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting network metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/statistics')
def get_statistics():
    """
    Get aggregated metric statistics.
    
    Query Parameters:
        hours: Number of hours to analyze (default: 24)
        
    Returns:
        JSON with statistical summaries
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = max(1, min(hours, 168))
        
        stats = Metric.get_statistics(hours=hours)
        
        if not stats:
            return jsonify({
                'success': True,
                'data': None,
                'message': 'Insufficient data for statistics'
            })
        
        return jsonify({
            'success': True,
            'data': stats,
            'hours': hours
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/system-info')
def get_system_info():
    """
    Get static system information.
    
    Returns:
        JSON with system details (CPU count, total memory, etc.)
    """
    try:
        info = MetricsCollector.get_system_info()
        
        # Format values
        if 'memory_total' in info:
            info['memory_total_formatted'] = MetricsCollector.format_bytes(info['memory_total'])
        if 'disk_total' in info:
            info['disk_total_formatted'] = MetricsCollector.format_bytes(info['disk_total'])
        
        return jsonify({
            'success': True,
            'data': info
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting system info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
