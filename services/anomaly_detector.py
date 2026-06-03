"""
Machine learning anomaly detection service using Isolation Forest.
Detects abnormal patterns in server metrics.
"""

import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Anomaly detection using Isolation Forest algorithm.
    
    Isolation Forest works by isolating observations through random partitioning.
    Anomalies are easier to isolate (require fewer partitions), so they have
    shorter path lengths in the tree structure.
    
    Attributes:
        model: Trained IsolationForest model
        scaler: StandardScaler for feature normalization
        is_trained: Whether the model has been trained
        contamination: Expected proportion of anomalies in data
        min_samples: Minimum samples required for training
    """
    
    FEATURE_NAMES = ['cpu_usage', 'memory_usage', 'disk_usage', 'network_rate']
    MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_artifacts')
    MODEL_PATH = os.path.join(MODEL_DIR, 'isolation_forest.joblib')
    SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.joblib')
    
    def __init__(self, contamination: float = 0.05, min_samples: int = 100):
        """
        Initialize the anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
            min_samples: Minimum number of samples required to train
        """
        self.contamination = contamination
        self.min_samples = min_samples
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.last_training_time = None
        self.training_sample_count = 0
        
        # Try to load existing model
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load saved model and scaler if they exist."""
        try:
            if os.path.exists(self.MODEL_PATH) and os.path.exists(self.SCALER_PATH):
                self.model = joblib.load(self.MODEL_PATH)
                self.scaler = joblib.load(self.SCALER_PATH)
                self.is_trained = True
                logger.info("Loaded existing anomaly detection model")
                return True
        except Exception as e:
            logger.warning(f"Failed to load existing model: {e}")
        return False
    
    def _save_model(self):
        """Save model and scaler to disk."""
        try:
            os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
            joblib.dump(self.model, self.MODEL_PATH)
            joblib.dump(self.scaler, self.SCALER_PATH)
            logger.info("Saved anomaly detection model")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def _extract_features(self, metrics: List[Dict]) -> np.ndarray:
        """
        Extract feature matrix from metrics list.
        
        Features:
        - cpu_usage: CPU utilization percentage
        - memory_usage: Memory utilization percentage  
        - disk_usage: Disk utilization percentage
        - network_rate: Combined network throughput (normalized)
        
        Args:
            metrics: List of metric dictionaries or Metric objects
            
        Returns:
            2D numpy array of shape (n_samples, n_features)
        """
        features = []
        
        for m in metrics:
            # Handle both dict and ORM object
            if hasattr(m, 'to_dict'):
                m = m.to_dict()
            elif hasattr(m, '__dict__'):
                m = {k: v for k, v in m.__dict__.items() if not k.startswith('_')}
            
            # Calculate combined network rate (MB/s)
            sent_rate = m.get('network_sent_rate', 0) or 0
            recv_rate = m.get('network_received_rate', 0) or 0
            network_rate = (sent_rate + recv_rate) / (1024 * 1024)  # Convert to MB/s
            
            features.append([
                m.get('cpu_usage', 0) or 0,
                m.get('memory_usage', 0) or 0,
                m.get('disk_usage', 0) or 0,
                network_rate
            ])
        
        return np.array(features)
    
    def train(self, metrics: List) -> bool:
        """
        Train the Isolation Forest model on historical metrics.
        
        Args:
            metrics: List of Metric objects or dictionaries
            
        Returns:
            True if training succeeded, False otherwise
        """
        if len(metrics) < self.min_samples:
            logger.warning(f"Insufficient samples for training: {len(metrics)} < {self.min_samples}")
            return False
        
        try:
            # Extract features
            X = self._extract_features(metrics)
            
            # Initialize and fit scaler
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Initialize and train Isolation Forest
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=100,
                max_samples='auto',
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_scaled)
            
            self.is_trained = True
            self.last_training_time = datetime.utcnow()
            self.training_sample_count = len(metrics)
            
            # Save model
            self._save_model()
            
            logger.info(f"Trained anomaly detector on {len(metrics)} samples")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to train anomaly detector: {e}")
            return False
    
    def detect(self, metric: Dict) -> Tuple[bool, float, str]:
        """
        Detect if a single metric is anomalous.
        
        Args:
            metric: Single metric dictionary or Metric object
            
        Returns:
            Tuple of (is_anomaly, anomaly_score, severity)
            - is_anomaly: Boolean indicating anomaly
            - anomaly_score: Score from -1 (anomaly) to 1 (normal)
            - severity: 'normal', 'warning', or 'critical'
        """
        if not self.is_trained or self.model is None or self.scaler is None:
            logger.warning("Anomaly detector not trained, using threshold-based detection")
            return self._threshold_detect(metric)
        
        try:
            # Extract features
            X = self._extract_features([metric])
            X_scaled = self.scaler.transform(X)
            
            # Get prediction (-1 = anomaly, 1 = normal)
            prediction = self.model.predict(X_scaled)[0]
            
            # Get anomaly score (more negative = more anomalous)
            anomaly_score = self.model.decision_function(X_scaled)[0]
            
            is_anomaly = prediction == -1
            
            # Determine severity
            from models.anomaly import Anomaly
            severity = Anomaly.score_to_severity(anomaly_score, is_anomaly)
            
            return is_anomaly, float(anomaly_score), severity
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return self._threshold_detect(metric)
    
    def _threshold_detect(self, metric: Dict) -> Tuple[bool, float, str]:
        """
        Fallback threshold-based anomaly detection.
        
        Used when ML model is not trained.
        """
        if hasattr(metric, 'to_dict'):
            metric = metric.to_dict()
        
        cpu = metric.get('cpu_usage', 0) or 0
        memory = metric.get('memory_usage', 0) or 0
        disk = metric.get('disk_usage', 0) or 0
        
        # Simple threshold-based scoring
        issues = 0
        if cpu > 90:
            issues += 2
        elif cpu > 70:
            issues += 1
        
        if memory > 90:
            issues += 2
        elif memory > 75:
            issues += 1
        
        if disk > 95:
            issues += 2
        elif disk > 80:
            issues += 1
        
        if issues >= 3:
            return True, -0.5, 'critical'
        elif issues >= 1:
            return True, -0.2, 'warning'
        else:
            return False, 0.5, 'normal'
    
    def detect_and_store(self, metric, db_session) -> Optional['Anomaly']:
        """
        Detect anomaly and store result in database.
        
        Args:
            metric: Metric object or dictionary
            db_session: SQLAlchemy database session
            
        Returns:
            Created Anomaly instance or None
        """
        from models.anomaly import Anomaly
        
        try:
            is_anomaly, score, severity = self.detect(metric)
            
            if hasattr(metric, 'to_dict'):
                metric_dict = metric.to_dict()
            else:
                metric_dict = metric
            
            # Determine primary metric that triggered anomaly
            metric_name = 'system'
            metric_value = metric_dict.get('cpu_usage', 0)
            
            cpu = metric_dict.get('cpu_usage', 0) or 0
            memory = metric_dict.get('memory_usage', 0) or 0
            disk = metric_dict.get('disk_usage', 0) or 0
            
            if cpu > memory and cpu > disk:
                metric_name = 'cpu'
                metric_value = cpu
            elif memory > disk:
                metric_name = 'memory'
                metric_value = memory
            else:
                metric_name = 'disk'
                metric_value = disk
            
            anomaly = Anomaly(
                metric_name=metric_name,
                metric_value=metric_value,
                anomaly_score=score,
                is_anomaly=is_anomaly,
                severity=severity,
                features_json=json.dumps({
                    'cpu_usage': cpu,
                    'memory_usage': memory,
                    'disk_usage': disk,
                    'network_rate': (metric_dict.get('network_sent_rate', 0) or 0) + 
                                   (metric_dict.get('network_received_rate', 0) or 0)
                })
            )
            
            db_session.add(anomaly)
            db_session.commit()
            
            if is_anomaly:
                logger.info(f"Anomaly detected: {metric_name}={metric_value:.1f}, "
                           f"score={score:.4f}, severity={severity}")
            
            return anomaly
            
        except Exception as e:
            logger.error(f"Failed to detect and store anomaly: {e}")
            db_session.rollback()
            return None
    
    def get_status(self) -> Dict:
        """Get detector status information."""
        return {
            'is_trained': self.is_trained,
            'last_training_time': self.last_training_time.isoformat() if self.last_training_time else None,
            'training_sample_count': self.training_sample_count,
            'contamination': self.contamination,
            'min_samples': self.min_samples,
            'feature_names': self.FEATURE_NAMES
        }
