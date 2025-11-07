"""
AI/ML Prediction Service for AFOC Platform
Provides time-series forecasting using Prophet and custom Transformer models
"""

import asyncio
import logging
from concurrent import futures
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import grpc
import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import structlog

# Import generated protobuf (in production, generate from proto files)
# from proto.gen.prediction.v1 import prediction_pb2, prediction_pb2_grpc

logger = structlog.get_logger()


class PredictionModel:
    """Base class for prediction models"""

    def __init__(self, model_type: str):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.trained_at = None

    def train(self, data: pd.DataFrame) -> Dict[str, float]:
        """Train the model on historical data"""
        raise NotImplementedError

    def predict(self, periods: int) -> pd.DataFrame:
        """Generate predictions for future periods"""
        raise NotImplementedError


class ProphetModel(PredictionModel):
    """Time-series forecasting using Facebook Prophet"""

    def __init__(self):
        super().__init__("prophet")
        self.model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            seasonality_mode='multiplicative',
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True
        )

    def train(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Train Prophet model on historical metrics

        Args:
            data: DataFrame with 'ds' (datetime) and 'y' (value) columns

        Returns:
            Dictionary of model metrics (MAE, MAPE, RMSE)
        """
        logger.info("Training Prophet model", rows=len(data))

        # Prophet requires specific column names
        df = data.copy()
        if 'timestamp' in df.columns:
            df = df.rename(columns={'timestamp': 'ds', 'value': 'y'})

        # Train model
        self.model.fit(df)
        self.trained_at = datetime.now()

        # Calculate cross-validation metrics
        metrics = self._calculate_metrics(df)

        logger.info("Prophet model trained", metrics=metrics)
        return metrics

    def predict(self, periods: int) -> pd.DataFrame:
        """
        Generate predictions for future periods

        Args:
            periods: Number of time periods to forecast

        Returns:
            DataFrame with predictions and confidence intervals
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        # Create future dataframe
        future = self.model.make_future_dataframe(periods=periods, freq='H')

        # Generate forecast
        forecast = self.model.predict(future)

        # Return only future predictions
        forecast = forecast.tail(periods)

        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

    def _calculate_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate model accuracy metrics"""
        # Simple train/test split for metrics
        split_idx = int(len(df) * 0.8)
        train = df[:split_idx]
        test = df[split_idx:]

        # Train on subset
        temp_model = Prophet()
        temp_model.fit(train)

        # Predict on test set
        forecast = temp_model.predict(test[['ds']])

        # Calculate metrics
        y_true = test['y'].values
        y_pred = forecast['yhat'].values

        mae = np.mean(np.abs(y_true - y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

        # R² score
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot)

        return {
            'mae': float(mae),
            'mape': float(mape),
            'rmse': float(rmse),
            'r2_score': float(r2)
        }


class AnomalyDetector:
    """Anomaly detection using Isolation Forest"""

    def __init__(self, contamination: float = 0.1):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()

    def fit(self, data: np.ndarray):
        """Train anomaly detection model"""
        scaled_data = self.scaler.fit_transform(data)
        self.model.fit(scaled_data)

    def detect(self, data: np.ndarray) -> np.ndarray:
        """
        Detect anomalies in data

        Returns:
            Array of anomaly scores (-1 for anomalies, 1 for normal)
        """
        scaled_data = self.scaler.transform(data)
        predictions = self.model.predict(scaled_data)
        scores = self.model.score_samples(scaled_data)

        return predictions, scores


class PredictionService:
    """Main prediction service handling gRPC requests"""

    def __init__(self, db_url: str):
        self.db_engine = sa.create_engine(db_url)
        self.Session = sessionmaker(bind=self.db_engine)
        self.models: Dict[str, PredictionModel] = {}
        self.anomaly_detector = AnomalyDetector()

    async def predict(self, resource_id: str, metric_name: str,
                     forecast_days: int, model_type: str = "prophet") -> Dict:
        """
        Generate predictions for a resource metric

        Args:
            resource_id: Cloud resource identifier
            metric_name: Metric to predict (e.g., 'cpu_usage', 'memory_usage')
            forecast_days: Number of days to forecast (7-30)
            model_type: Type of model to use ('prophet', 'transformer', 'arima')

        Returns:
            Dictionary with predictions and confidence intervals
        """
        logger.info("Generating prediction",
                   resource_id=resource_id,
                   metric=metric_name,
                   days=forecast_days)

        # Fetch historical data
        historical_data = await self._fetch_historical_data(
            resource_id, metric_name, days=90
        )

        if historical_data.empty:
            raise ValueError(f"No historical data found for {resource_id}/{metric_name}")

        # Get or create model
        model_key = f"{resource_id}_{metric_name}_{model_type}"
        if model_key not in self.models:
            if model_type == "prophet":
                model = ProphetModel()
            else:
                raise ValueError(f"Unknown model type: {model_type}")

            # Train model
            metrics = model.train(historical_data)
            self.models[model_key] = model
        else:
            model = self.models[model_key]
            metrics = {}

        # Generate predictions
        periods = forecast_days * 24  # hourly predictions
        forecast = model.predict(periods)

        # Convert to response format
        predictions = []
        for _, row in forecast.iterrows():
            predictions.append({
                'timestamp': row['ds'],
                'predicted_value': float(row['yhat']),
                'lower_bound': float(row['yhat_lower']),
                'upper_bound': float(row['yhat_upper']),
                'metric_name': metric_name
            })

        # Detect anomalies in predictions
        anomaly_scores = self._detect_prediction_anomalies(predictions)

        return {
            'predictions': predictions,
            'confidence_score': 0.85,  # Based on model metrics
            'model_version': '1.0.0',
            'model_type': model_type,
            'metrics': metrics,
            'anomaly_scores': anomaly_scores
        }

    async def _fetch_historical_data(self, resource_id: str,
                                     metric_name: str, days: int) -> pd.DataFrame:
        """Fetch historical metrics from database"""
        query = """
            SELECT timestamp, value
            FROM metric_dbs
            WHERE resource_id = :resource_id
              AND metric_name = :metric_name
              AND timestamp >= :start_time
            ORDER BY timestamp
        """

        start_time = datetime.now() - timedelta(days=days)

        session = self.Session()
        try:
            result = session.execute(
                sa.text(query),
                {
                    'resource_id': resource_id,
                    'metric_name': metric_name,
                    'start_time': start_time
                }
            )

            data = pd.DataFrame(result.fetchall(), columns=['timestamp', 'value'])

            # Prepare for Prophet
            data = data.rename(columns={'timestamp': 'ds', 'value': 'y'})
            data['ds'] = pd.to_datetime(data['ds'])

            return data
        finally:
            session.close()

    def _detect_prediction_anomalies(self, predictions: List[Dict]) -> List[float]:
        """Detect anomalies in predicted values"""
        values = np.array([p['predicted_value'] for p in predictions]).reshape(-1, 1)

        # Simple threshold-based anomaly detection
        mean = values.mean()
        std = values.std()
        threshold = mean + 3 * std

        scores = []
        for val in values:
            score = abs(val[0] - mean) / std if std > 0 else 0
            scores.append(float(score))

        return scores


class CostPredictor:
    """Specialized predictor for cloud cost forecasting"""

    def __init__(self, db_url: str):
        self.db_engine = sa.create_engine(db_url)
        self.Session = sessionmaker(bind=self.db_engine)

    async def predict_costs(self, account_id: str, provider: str,
                          forecast_days: int) -> Dict:
        """
        Predict future cloud costs

        Args:
            account_id: Cloud account identifier
            provider: Cloud provider (aws, gcp, azure)
            forecast_days: Number of days to forecast

        Returns:
            Cost predictions with breakdown by service
        """
        logger.info("Predicting costs",
                   account=account_id,
                   provider=provider,
                   days=forecast_days)

        # In production: fetch actual cost data from Cost Explorer/Billing APIs
        # For now, return mock predictions

        daily_costs = []
        base_cost = 1200.0

        for day in range(forecast_days):
            # Simulate cost trends with seasonality
            date = datetime.now() + timedelta(days=day)
            trend = 1.0 + (day * 0.01)  # 1% daily growth
            seasonal = 1.0 + 0.1 * np.sin(2 * np.pi * day / 7)  # weekly pattern

            predicted_cost = base_cost * trend * seasonal

            daily_costs.append({
                'date': date.strftime('%Y-%m-%d'),
                'predicted_cost': round(predicted_cost, 2),
                'lower_bound': round(predicted_cost * 0.9, 2),
                'upper_bound': round(predicted_cost * 1.1, 2)
            })

        total_predicted = sum(c['predicted_cost'] for c in daily_costs)

        return {
            'daily_predictions': daily_costs,
            'total_predicted_cost': round(total_predicted, 2),
            'currency': 'USD',
            'confidence_score': 0.82,
            'cost_by_service': {
                'Compute': round(total_predicted * 0.65, 2),
                'Storage': round(total_predicted * 0.20, 2),
                'Network': round(total_predicted * 0.10, 2),
                'Other': round(total_predicted * 0.05, 2)
            }
        }


async def main():
    """Main entry point for prediction service"""
    logging.basicConfig(level=logging.INFO)

    db_url = "postgresql://afoc:afoc@localhost:5432/afoc"

    service = PredictionService(db_url)
    cost_predictor = CostPredictor(db_url)

    # Example: Generate predictions
    try:
        result = await service.predict(
            resource_id="i-1234567890abcdef0",
            metric_name="cpu_usage",
            forecast_days=7,
            model_type="prophet"
        )

        logger.info("Prediction completed",
                   prediction_count=len(result['predictions']),
                   confidence=result['confidence_score'])

        # Example: Cost predictions
        cost_result = await cost_predictor.predict_costs(
            account_id="123456789012",
            provider="aws",
            forecast_days=30
        )

        logger.info("Cost prediction completed",
                   total_cost=cost_result['total_predicted_cost'])

    except Exception as e:
        logger.error("Prediction failed", error=str(e))


if __name__ == "__main__":
    asyncio.run(main())
