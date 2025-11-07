# AFOC - Autonomous Fiscal Orchestration Core

[![AFOC CI/CD Pipeline](https://github.com/NorCal-Quake-Prep-Thanksgiving-25/AFOC/actions/workflows/ci.yml/badge.svg)](https://github.com/NorCal-Quake-Prep-Thanksgiving-25/AFOC/actions/workflows/ci.yml)
[![CodeQL](https://github.com/NorCal-Quake-Prep-Thanksgiving-25/AFOC/actions/workflows/codeql.yml/badge.svg)](https://github.com/NorCal-Quake-Prep-Thanksgiving-25/AFOC/actions/workflows/codeql.yml)

A comprehensive platform for autonomous fiscal orchestration and management.

## Project Structure

```
AFOC/
├── frontend/          # React-based frontend application
├── services/          # Go-based backend services
├── ml-engine/         # Python-based ML engine
├── k8s/              # Kubernetes manifests
├── terraform/        # Infrastructure as Code
└── .github/          # CI/CD workflows
```

## Components

### Frontend
- React 18.x application
- Modern UI for fiscal management
- Located in `frontend/`

### Backend Services
- Go 1.21+ microservices
- RESTful API endpoints
- Located in `services/`

### ML Engine
- Python 3.11+ ML models
- Flask-based API
- Located in `ml-engine/`

### Infrastructure
- Kubernetes deployments and services
- Terraform AWS infrastructure
- CI/CD with GitHub Actions

## Development

### Prerequisites
- Node.js 20+
- Go 1.21+
- Python 3.11+
- Docker
- Kubernetes (kubectl)
- Terraform 1.6+

### Local Development

#### Frontend
```bash
cd frontend
npm install
npm start
```

#### Backend Services
```bash
cd services
go mod download
go run cmd/api/main.go
```

#### ML Engine
```bash
cd ml-engine
pip install -r requirements.txt
python src/app.py
```

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment:

- **Frontend CI**: Linting, testing, and building the React application
- **Go Services CI**: Testing and building Go services
- **Kubernetes Validation**: Validating K8s manifests
- **ML Engine CI**: Python linting and testing
- **Terraform Validation**: Infrastructure code validation
- **Security Scanning**: Trivy vulnerability scanning
- **Docker Image Building**: Multi-stage container builds
- **Deployment**: Automated deployments to staging and production

## Security

- All dependencies are regularly scanned with Trivy
- CodeQL analysis for code security
- Secure Docker images with minimal attack surface
- Infrastructure security best practices

## License

See LICENSE file for details.
