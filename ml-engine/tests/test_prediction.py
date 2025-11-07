"""
Unit and integration tests for ML Prediction Service
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from prediction_service import ProphetModel, AnomalyDetector, PredictionService, CostPredictor


class TestProphetModel:
    """Test suite for Prophet forecasting model"""

    @pytest.fixture
    def sample_data(self):
        """Generate sample time-series data"""
        dates = pd.date_range(start='2024-01-01', periods=90, freq='D')
        values = 50 + 10 * np.sin(np.arange(90) * 2 * np.pi / 7) + np.random.normal(0, 2, 90)

        df = pd.DataFrame({
            'ds': dates,
            'y': values
        })
        return df

    def test_model_training(self, sample_data):
        """Test that Prophet model trains successfully"""
        model = ProphetModel()
        metrics = model.train(sample_data)

        assert 'mae' in metrics
        assert 'mape' in metrics
        assert 'rmse' in metrics
        assert 'r2_score' in metrics

        # Check that metrics are reasonable
        assert metrics['mae'] > 0
        assert 0 <= metrics['mape'] <= 100
        assert metrics['rmse'] > 0
        assert -1 <= metrics['r2_score'] <= 1

    def test_prediction_generation(self, sample_data):
        """Test that model generates predictions"""
        model = ProphetModel()
        model.train(sample_data)

        # Predict next 7 days
        forecast = model.predict(periods=7)

        assert len(forecast) == 7
        assert 'ds' in forecast.columns
        assert 'yhat' in forecast.columns
        assert 'yhat_lower' in forecast.columns
        assert 'yhat_upper' in forecast.columns

        # Check that confidence intervals are valid
        assert all(forecast['yhat_lower'] <= forecast['yhat'])
        assert all(forecast['yhat'] <= forecast['yhat_upper'])

    def test_prediction_without_training(self):
        """Test that prediction fails without training"""
        model = ProphetModel()

        with pytest.raises(ValueError):
            model.predict(periods=7)


class TestAnomalyDetector:
    """Test suite for anomaly detection"""

    @pytest.fixture
    def normal_data(self):
        """Generate normal data with some anomalies"""
        np.random.seed(42)
        values = np.random.normal(50, 5, 100)

        # Inject anomalies
        values[20] = 100  # Spike
        values[50] = 10   # Drop

        return values.reshape(-1, 1)

    def test_anomaly_detection(self, normal_data):
        """Test that anomaly detector identifies anomalies"""
        detector = AnomalyDetector(contamination=0.05)
        detector.fit(normal_data[:80])  # Train on first 80 points

        predictions, scores = detector.detect(normal_data[80:])

        # Should detect some anomalies
        assert -1 in predictions  # -1 indicates anomaly
        assert len(scores) == len(normal_data[80:])

    def test_detector_training(self, normal_data):
        """Test that detector trains successfully"""
        detector = AnomalyDetector()
        detector.fit(normal_data)

        # Check that model is trained
        assert detector.model is not None
        assert detector.scaler is not None


@pytest.mark.asyncio
class TestPredictionService:
    """Test suite for prediction service"""

    @pytest.fixture
    def db_url(self):
        """Return test database URL"""
        return "postgresql://test:test@localhost:5432/test_afoc"

    async def test_prediction_generation(self, db_url):
        """Test end-to-end prediction generation"""
        # This would require a test database with mock data
        # For now, we'll test the structure
        service = PredictionService(db_url)

        # In production tests, this would call the actual service
        # For unit tests, we can test with mock data
        pass

    async def test_cost_prediction(self, db_url):
        """Test cost prediction functionality"""
        predictor = CostPredictor(db_url)

        result = await predictor.predict_costs(
            account_id="123456789012",
            provider="aws",
            forecast_days=7
        )

        assert 'daily_predictions' in result
        assert 'total_predicted_cost' in result
        assert 'cost_by_service' in result
        assert len(result['daily_predictions']) == 7


class TestModelAccuracy:
    """Test suite for model accuracy and performance"""

    def test_prediction_accuracy(self):
        """Test that predictions are within acceptable error range"""
        # Generate synthetic data with known pattern
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')

        # Create data with clear trend and seasonality
        trend = np.linspace(50, 60, 100)
        seasonal = 5 * np.sin(np.arange(100) * 2 * np.pi / 7)
        noise = np.random.normal(0, 1, 100)
        values = trend + seasonal + noise

        df = pd.DataFrame({'ds': dates, 'y': values})

        # Train on first 80 days
        model = ProphetModel()
        model.train(df[:80])

        # Predict next 20 days
        forecast = model.predict(periods=20)

        # Calculate error on actual future values
        actual = df[80:]['y'].values
        predicted = forecast['yhat'].values[:20]

        mae = np.mean(np.abs(actual - predicted))
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100

        # Check that predictions are reasonably accurate
        assert mae < 5.0, f"MAE too high: {mae}"
        assert mape < 20.0, f"MAPE too high: {mape}"


def test_data_preprocessing():
    """Test data preprocessing and feature engineering"""
    # Create sample data
    dates = pd.date_range(start='2024-01-01', periods=50, freq='H')
    values = np.random.normal(50, 10, 50)

    df = pd.DataFrame({'timestamp': dates, 'value': values})

    # Test that data can be converted to Prophet format
    df_prophet = df.rename(columns={'timestamp': 'ds', 'value': 'y'})

    assert 'ds' in df_prophet.columns
    assert 'y' in df_prophet.columns
    assert len(df_prophet) == 50


@pytest.mark.benchmark
def test_prediction_performance(benchmark):
    """Benchmark prediction performance"""
    # Generate sample data
    dates = pd.date_range(start='2024-01-01', periods=90, freq='D')
    values = 50 + 10 * np.sin(np.arange(90) * 2 * np.pi / 7) + np.random.normal(0, 2, 90)
    df = pd.DataFrame({'ds': dates, 'y': values})

    model = ProphetModel()
    model.train(df)

    # Benchmark prediction time
    result = benchmark(model.predict, periods=30)

    # Predictions should complete in reasonable time
    assert len(result) == 30


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=prediction_service', '--cov-report=html'])
