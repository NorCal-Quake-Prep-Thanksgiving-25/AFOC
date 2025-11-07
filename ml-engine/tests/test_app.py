import pytest
import json
from src.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'afoc-ml-engine'

def test_model_info(client):
    """Test model info endpoint"""
    response = client.get('/api/model/info')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'model_name' in data
    assert 'version' in data
    assert data['status'] == 'active'

def test_predict(client):
    """Test prediction endpoint"""
    test_data = {'input': 'test_value'}
    response = client.post('/api/predict',
                          data=json.dumps(test_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'prediction' in data
