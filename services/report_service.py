"""
Report generation service.
Generates CSV and PDF reports from monitoring data.
"""

import csv
import io
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportService:
    """
    Generates monitoring reports in CSV and PDF formats.
    """
    
    def __init__(self, reports_dir: str = 'reports'):
        """
        Initialize report service.
        
        Args:
            reports_dir: Directory to save generated reports
        """
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
    
    def generate_csv_report(
        self,
        metrics: List,
        alerts: List,
        anomalies: List,
        hours: int = 24
    ) -> str:
        """
        Generate a CSV report.
        
        Args:
            metrics: List of Metric objects
            alerts: List of Alert objects
            anomalies: List of Anomaly objects
            hours: Report time window
            
        Returns:
            CSV content as string
        """
        output = io.StringIO()
        
        # Write report header
        output.write(f"Server Monitoring Report\n")
        output.write(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        output.write(f"Period: Last {hours} hours\n")
        output.write("\n")
        
        # Metrics section
        output.write("=== METRICS ===\n")
        if metrics:
            writer = csv.writer(output)
            writer.writerow([
                'Timestamp', 'CPU %', 'Memory %', 'Disk %',
                'Network Sent (B/s)', 'Network Recv (B/s)',
                'Process Count', 'Health Score'
            ])
            
            for m in metrics:
                if hasattr(m, 'to_dict'):
                    m = m.to_dict()
                writer.writerow([
                    m.get('created_at', ''),
                    round(m.get('cpu_usage', 0), 2),
                    round(m.get('memory_usage', 0), 2),
                    round(m.get('disk_usage', 0), 2),
                    round(m.get('network_sent_rate', 0), 2),
                    round(m.get('network_received_rate', 0), 2),
                    m.get('process_count', 0),
                    round(m.get('health_score', 0), 2)
                ])
        else:
            output.write("No metrics data available\n")
        
        output.write("\n")
        
        # Alerts section
        output.write("=== ALERTS ===\n")
        if alerts:
            writer = csv.writer(output)
            writer.writerow([
                'Timestamp', 'Severity', 'Metric', 'Value', 'Status', 'Message'
            ])
            
            for a in alerts:
                if hasattr(a, 'to_dict'):
                    a = a.to_dict()
                writer.writerow([
                    a.get('created_at', ''),
                    a.get('severity', ''),
                    a.get('metric_name', ''),
                    round(a.get('metric_value', 0), 2),
                    a.get('status', ''),
                    a.get('message', '')[:100]
                ])
        else:
            output.write("No alerts in this period\n")
        
        output.write("\n")
        
        # Anomalies section
        output.write("=== ANOMALIES ===\n")
        if anomalies:
            writer = csv.writer(output)
            writer.writerow([
                'Timestamp', 'Metric', 'Value', 'Anomaly Score', 'Severity'
            ])
            
            for an in anomalies:
                if hasattr(an, 'to_dict'):
                    an = an.to_dict()
                if an.get('is_anomaly'):
                    writer.writerow([
                        an.get('created_at', ''),
                        an.get('metric_name', ''),
                        round(an.get('metric_value', 0), 2),
                        round(an.get('anomaly_score', 0), 4),
                        an.get('severity', '')
                    ])
        else:
            output.write("No anomalies detected in this period\n")
        
        content = output.getvalue()
        output.close()
        
        return content
    
    def generate_pdf_report(
        self,
        metrics_stats: Dict,
        alert_stats: Dict,
        anomaly_stats: Dict,
        hours: int = 24
    ) -> bytes:
        """
        Generate a PDF report.
        
        Args:
            metrics_stats: Metrics statistics dictionary
            alert_stats: Alert statistics dictionary
            anomaly_stats: Anomaly statistics dictionary
            hours: Report time window
            
        Returns:
            PDF content as bytes
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph("Server Monitoring Report", title_style))
        elements.append(Paragraph(
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            styles['Normal']
        ))
        elements.append(Paragraph(f"Period: Last {hours} hours", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Summary Section
        elements.append(Paragraph("Executive Summary", heading_style))
        
        health_avg = metrics_stats.get('health_avg', 'N/A')
        total_alerts = alert_stats.get('total', 0)
        total_anomalies = anomaly_stats.get('total_anomalies', 0)
        
        summary_text = f"""
        Overall system health score: <b>{health_avg}</b><br/>
        Total alerts generated: <b>{total_alerts}</b><br/>
        Anomalies detected: <b>{total_anomalies}</b><br/>
        Data points collected: <b>{metrics_stats.get('total_records', 0)}</b>
        """
        elements.append(Paragraph(summary_text, styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Metrics Statistics
        elements.append(Paragraph("System Metrics", heading_style))
        
        metrics_data = [
            ['Metric', 'Average', 'Minimum', 'Maximum'],
            [
                'CPU Usage (%)',
                str(metrics_stats.get('cpu', {}).get('avg', 'N/A')),
                str(metrics_stats.get('cpu', {}).get('min', 'N/A')),
                str(metrics_stats.get('cpu', {}).get('max', 'N/A'))
            ],
            [
                'Memory Usage (%)',
                str(metrics_stats.get('memory', {}).get('avg', 'N/A')),
                str(metrics_stats.get('memory', {}).get('min', 'N/A')),
                str(metrics_stats.get('memory', {}).get('max', 'N/A'))
            ],
            [
                'Disk Usage (%)',
                str(metrics_stats.get('disk', {}).get('avg', 'N/A')),
                str(metrics_stats.get('disk', {}).get('min', 'N/A')),
                str(metrics_stats.get('disk', {}).get('max', 'N/A'))
            ]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 20))
        
        # Alert Statistics
        elements.append(Paragraph("Alert Summary", heading_style))
        
        by_severity = alert_stats.get('by_severity', {})
        alert_data = [
            ['Severity', 'Count'],
            ['Critical', str(by_severity.get('critical', 0))],
            ['Warning', str(by_severity.get('warning', 0))],
            ['Info', str(by_severity.get('info', 0))],
            ['Total', str(alert_stats.get('total', 0))]
        ]
        
        alert_table = Table(alert_data, colWidths=[2*inch, 2*inch])
        alert_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(alert_table)
        elements.append(Spacer(1, 20))
        
        # Anomaly Statistics
        elements.append(Paragraph("Anomaly Detection", heading_style))
        
        anomaly_text = f"""
        Total metrics analyzed: <b>{anomaly_stats.get('total_analyzed', 0)}</b><br/>
        Anomalies detected: <b>{anomaly_stats.get('total_anomalies', 0)}</b><br/>
        Anomaly rate: <b>{anomaly_stats.get('anomaly_rate', 0)}%</b>
        """
        elements.append(Paragraph(anomaly_text, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    
    def save_report(
        self,
        content: bytes | str,
        filename: str,
        is_binary: bool = False
    ) -> str:
        """
        Save a report to the reports directory.
        
        Args:
            content: Report content
            filename: Output filename
            is_binary: Whether content is binary (PDF) or text (CSV)
            
        Returns:
            Full path to saved file
        """
        filepath = os.path.join(self.reports_dir, filename)
        
        mode = 'wb' if is_binary else 'w'
        with open(filepath, mode) as f:
            f.write(content)
        
        logger.info(f"Report saved: {filepath}")
        
        return filepath
