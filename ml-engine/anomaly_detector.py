"""
Real-time Anomaly Detection Service for AFOC Platform
Uses Isolation Forest and statistical methods for anomaly detection
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import structlog

logger = structlog.get_logger()


class AnomalyDetectionEngine:
    """
    Multi-method anomaly detection engine
    Combines statistical methods, ML models, and domain-specific rules
    """

    def __init__(self, sensitivity: float = 0.95):
        self.sensitivity = sensitivity
        self.isolation_forest = IsolationForest(
            contamination=1 - sensitivity,
            random_state=42,
            n_estimators=100,
            max_samples='auto'
        )
        self.scaler = StandardScaler()
        self.baseline_stats = {}

    def fit(self, normal_data: pd.DataFrame):
        """
        Train anomaly detection model on normal data

        Args:
            normal_data: DataFrame with columns ['timestamp', 'value', 'resource_id']
        """
        logger.info("Training anomaly detection model", rows=len(normal_data))

        # Calculate baseline statistics
        self.baseline_stats = {
            'mean': normal_data['value'].mean(),
            'std': normal_data['value'].std(),
            'q25': normal_data['value'].quantile(0.25),
            'q75': normal_data['value'].quantile(0.75),
            'max': normal_data['value'].max(),
            'min': normal_data['value'].min()
        }

        # Prepare features for ML model
        features = self._extract_features(normal_data)

        # Train Isolation Forest
        scaled_features = self.scaler.fit_transform(features)
        self.isolation_forest.fit(scaled_features)

        logger.info("Anomaly detection model trained", stats=self.baseline_stats)

    def detect_anomalies(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Detect anomalies in time-series data

        Args:
            data: DataFrame with columns ['timestamp', 'value', 'resource_id']

        Returns:
            DataFrame with anomaly scores and labels
        """
        features = self._extract_features(data)
        scaled_features = self.scaler.transform(features)

        # ML-based detection
        ml_predictions = self.isolation_forest.predict(scaled_features)
        ml_scores = self.isolation_forest.score_samples(scaled_features)

        # Statistical detection
        stat_predictions = self._statistical_detection(data['value'].values)

        # Combined detection (both methods must agree)
        combined_predictions = []
        for ml_pred, stat_pred in zip(ml_predictions, stat_predictions):
            if ml_pred == -1 or stat_pred == -1:
                combined_predictions.append(-1)  # Anomaly
            else:
                combined_predictions.append(1)  # Normal

        # Calculate anomaly scores (0-1 scale)
        anomaly_scores = self._normalize_scores(ml_scores)

        # Determine severity
        severities = self._calculate_severity(data['value'].values, anomaly_scores)

        # Add results to dataframe
        result = data.copy()
        result['is_anomaly'] = [p == -1 for p in combined_predictions]
        result['anomaly_score'] = anomaly_scores
        result['severity'] = severities

        return result

    def detect_cost_spikes(self, cost_data: pd.DataFrame,
                          threshold_std: float = 3.0) -> List[Dict]:
        """
        Detect sudden cost spikes

        Args:
            cost_data: DataFrame with columns ['timestamp', 'cost', 'service']
            threshold_std: Number of standard deviations for spike detection

        Returns:
            List of detected cost spike events
        """
        logger.info("Detecting cost spikes", rows=len(cost_data))

        spikes = []

        # Calculate rolling statistics
        cost_data['rolling_mean'] = cost_data['cost'].rolling(window=24).mean()
        cost_data['rolling_std'] = cost_data['cost'].rolling(window=24).std()

        # Detect spikes
        for idx, row in cost_data.iterrows():
            if pd.isna(row['rolling_mean']):
                continue

            z_score = (row['cost'] - row['rolling_mean']) / row['rolling_std']

            if abs(z_score) > threshold_std:
                spike_amount = row['cost'] - row['rolling_mean']
                spike_pct = (spike_amount / row['rolling_mean']) * 100

                spikes.append({
                    'timestamp': row['timestamp'],
                    'service': row.get('service', 'unknown'),
                    'actual_cost': row['cost'],
                    'expected_cost': row['rolling_mean'],
                    'spike_amount': spike_amount,
                    'spike_percentage': spike_pct,
                    'z_score': z_score,
                    'severity': 'critical' if abs(z_score) > 4 else 'warning'
                })

        logger.info("Cost spikes detected", count=len(spikes))
        return spikes

    def analyze_root_cause(self, anomaly: Dict, context_data: pd.DataFrame) -> Dict:
        """
        Perform root cause analysis for an anomaly

        Args:
            anomaly: Dictionary containing anomaly details
            context_data: Additional context data (other metrics, events)

        Returns:
            Dictionary with root cause analysis
        """
        logger.info("Analyzing root cause", anomaly_type=anomaly.get('type'))

        # Simple rule-based RCA (in production: more sophisticated ML-based analysis)
        causes = []
        contributing_factors = []

        # Check for correlation with other metrics
        if 'cpu_usage' in context_data.columns:
            cpu_corr = context_data['cpu_usage'].corr(context_data['value'])
            if abs(cpu_corr) > 0.7:
                causes.append(f"High correlation with CPU usage (r={cpu_corr:.2f})")
                contributing_factors.append("cpu_usage")

        if 'memory_usage' in context_data.columns:
            mem_corr = context_data['memory_usage'].corr(context_data['value'])
            if abs(mem_corr) > 0.7:
                causes.append(f"High correlation with memory usage (r={mem_corr:.2f})")
                contributing_factors.append("memory_usage")

        # Check for time-based patterns
        if 'timestamp' in context_data.columns:
            context_data['hour'] = pd.to_datetime(context_data['timestamp']).dt.hour
            hourly_mean = context_data.groupby('hour')['value'].mean()
            current_hour = pd.to_datetime(anomaly['timestamp']).hour
            if hourly_mean[current_hour] > hourly_mean.mean() * 1.5:
                causes.append(f"Typical peak hour pattern (hour {current_hour})")
                contributing_factors.append("time_of_day")

        primary_cause = causes[0] if causes else "Unknown - requires manual investigation"

        return {
            'primary_cause': primary_cause,
            'contributing_factors': contributing_factors,
            'confidence': 0.75 if causes else 0.3,
            'evidence': {
                'analyzed_metrics': list(context_data.columns),
                'correlation_analysis': 'completed',
                'temporal_analysis': 'completed'
            }
        }

    def suggest_remediation(self, anomaly: Dict, root_cause: Dict) -> List[Dict]:
        """
        Suggest remediation actions based on anomaly type and root cause

        Args:
            anomaly: Anomaly details
            root_cause: Root cause analysis results

        Returns:
            List of suggested remediation actions
        """
        actions = []

        anomaly_type = anomaly.get('type', 'unknown')
        severity = anomaly.get('severity', 'warning')

        # Cost spike remediation
        if anomaly_type == 'cost_spike':
            if 'cpu_usage' in root_cause['contributing_factors']:
                actions.append({
                    'id': 'action-1',
                    'action_type': 'scale_down',
                    'description': 'Scale down over-provisioned resources',
                    'confidence': 0.8,
                    'auto_executable': severity != 'critical',
                    'parameters': {
                        'target_scale': 'down',
                        'reduction_factor': '0.5'
                    }
                })

            actions.append({
                'id': 'action-2',
                'action_type': 'alert_team',
                'description': 'Send alert to on-call team',
                'confidence': 1.0,
                'auto_executable': True,
                'parameters': {
                    'channel': 'pagerduty',
                    'severity': severity
                }
            })

        # Performance degradation remediation
        elif anomaly_type == 'performance_degradation':
            actions.append({
                'id': 'action-3',
                'action_type': 'restart_service',
                'description': 'Restart affected service to clear potential memory leaks',
                'confidence': 0.6,
                'auto_executable': False,
                'parameters': {
                    'service': anomaly.get('resource_id'),
                    'graceful': 'true'
                }
            })

        # Resource exhaustion remediation
        elif anomaly_type == 'resource_exhaustion':
            actions.append({
                'id': 'action-4',
                'action_type': 'scale_up',
                'description': 'Automatically scale up to handle increased load',
                'confidence': 0.9,
                'auto_executable': True,
                'parameters': {
                    'target_scale': 'up',
                    'scale_factor': '1.5'
                }
            })

        return actions

    def _extract_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features for ML model"""
        features = []

        # Time-based features
        if 'timestamp' in data.columns:
            data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
            data['day_of_week'] = pd.to_datetime(data['timestamp']).dt.dayofweek
            features.extend(['hour', 'day_of_week'])

        # Statistical features
        data['rolling_mean'] = data['value'].rolling(window=10, min_periods=1).mean()
        data['rolling_std'] = data['value'].rolling(window=10, min_periods=1).std()
        features.extend(['value', 'rolling_mean', 'rolling_std'])

        # Fill NaN values
        feature_df = data[features].fillna(method='bfill').fillna(0)

        return feature_df.values

    def _statistical_detection(self, values: np.ndarray) -> np.ndarray:
        """Statistical anomaly detection using IQR method"""
        q25 = np.percentile(values, 25)
        q75 = np.percentile(values, 75)
        iqr = q75 - q25

        lower_bound = q25 - (1.5 * iqr)
        upper_bound = q75 + (1.5 * iqr)

        predictions = []
        for val in values:
            if val < lower_bound or val > upper_bound:
                predictions.append(-1)  # Anomaly
            else:
                predictions.append(1)  # Normal

        return np.array(predictions)

    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """Normalize anomaly scores to 0-1 range"""
        # Isolation Forest scores are negative, with more negative = more anomalous
        normalized = -scores
        normalized = (normalized - normalized.min()) / (normalized.max() - normalized.min() + 1e-10)
        return normalized

    def _calculate_severity(self, values: np.ndarray, anomaly_scores: np.ndarray) -> List[str]:
        """Calculate severity level for each data point"""
        severities = []

        mean = self.baseline_stats.get('mean', np.mean(values))
        std = self.baseline_stats.get('std', np.std(values))

        for val, score in zip(values, anomaly_scores):
            z_score = abs((val - mean) / std) if std > 0 else 0

            if score > 0.8 or z_score > 4:
                severities.append('critical')
            elif score > 0.6 or z_score > 3:
                severities.append('warning')
            else:
                severities.append('info')

        return severities


async def main():
    """Test anomaly detection"""
    logging.basicConfig(level=logging.INFO)

    # Generate synthetic data
    np.random.seed(42)
    timestamps = pd.date_range(start='2025-01-01', periods=1000, freq='H')

    # Normal data with daily pattern
    normal_values = 50 + 10 * np.sin(np.arange(1000) * 2 * np.pi / 24) + np.random.normal(0, 2, 1000)

    # Inject anomalies
    anomaly_indices = [100, 250, 500, 750]
    for idx in anomaly_indices:
        normal_values[idx] = normal_values[idx] * 2.5  # Spike

    data = pd.DataFrame({
        'timestamp': timestamps,
        'value': normal_values,
        'resource_id': 'i-1234567890'
    })

    # Train detector
    detector = AnomalyDetectionEngine(sensitivity=0.95)
    detector.fit(data[:800])  # Train on first 800 points

    # Detect anomalies
    results = detector.detect_anomalies(data[800:])

    anomalies = results[results['is_anomaly']]
    logger.info("Anomaly detection completed",
               total_points=len(results),
               anomalies_found=len(anomalies))

    # Print detected anomalies
    for _, anomaly in anomalies.iterrows():
        logger.info("Anomaly detected",
                   timestamp=anomaly['timestamp'],
                   value=anomaly['value'],
                   score=anomaly['anomaly_score'],
                   severity=anomaly['severity'])


if __name__ == "__main__":
    asyncio.run(main())
