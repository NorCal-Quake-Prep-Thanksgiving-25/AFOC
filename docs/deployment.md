# AFOC Platform Deployment Guide

## Prerequisites

Before deploying AFOC, ensure you have:

- **Cloud Accounts**: AWS, GCP, and/or Azure with admin access
- **Kubernetes Cluster**: EKS, GKE, or AKS cluster (v1.28+)
- **Tools Installed**:
  - Terraform v1.6+
  - kubectl v1.28+
  - Helm v3.12+
  - Docker v24+
  - AWS CLI v2, gcloud CLI, az CLI (for respective clouds)

## Quick Start (15 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/afoc.git
cd afoc
```

### 2. Configure Cloud Credentials

**AWS**:
```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-east-1
```

**GCP**:
```bash
gcloud auth application-default login
export GOOGLE_PROJECT=your-project-id
```

**Azure**:
```bash
az login
export AZURE_SUBSCRIPTION_ID=your-subscription-id
```

### 3. Deploy Infrastructure with Terraform

```bash
cd terraform/

# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan -var="environment=prod" -var="gcp_project_id=your-project"

# Deploy infrastructure
terraform apply -var="environment=prod" -var="gcp_project_id=your-project"
```

**Outputs**:
- EKS cluster endpoint
- RDS PostgreSQL endpoint
- Redis cluster endpoint

### 4. Configure kubectl

**AWS EKS**:
```bash
aws eks update-kubeconfig --name afoc-cluster-prod --region us-east-1
```

**GCP GKE**:
```bash
gcloud container clusters get-credentials afoc-cluster-prod --region us-central1
```

**Azure AKS**:
```bash
az aks get-credentials --resource-group afoc-rg --name afoc-cluster-prod
```

### 5. Deploy AFOC Platform with Helm

```bash
cd ../k8s/

# Create namespace
kubectl apply -f namespace.yaml

# Install AFOC platform
helm install afoc ./helm/afoc \
  --namespace afoc \
  --set postgresql.auth.password=$(openssl rand -base64 32) \
  --set redis.auth.password=$(openssl rand -base64 32) \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="<IRSA_ROLE_ARN>"
```

### 6. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n afoc

# Wait for all pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=afoc -n afoc --timeout=300s

# Check services
kubectl get svc -n afoc

# View logs
kubectl logs -n afoc -l app.kubernetes.io/component=metrics-collector --tail=50
```

### 7. Access Dashboard

```bash
# Port-forward to frontend service
kubectl port-forward -n afoc svc/afoc-frontend 8080:80

# Open browser
open http://localhost:8080
```

## Production Deployment Checklist

### Security

- [ ] Enable TLS for all services (cert-manager + Let's Encrypt)
- [ ] Configure IAM roles with least privilege
- [ ] Enable encryption at rest for databases
- [ ] Set up AWS Secrets Manager for credentials
- [ ] Enable Kubernetes RBAC
- [ ] Configure network policies
- [ ] Enable pod security policies

### Monitoring

- [ ] Configure Prometheus retention (30 days)
- [ ] Set up Grafana dashboards
- [ ] Configure AlertManager with PagerDuty/Slack
- [ ] Enable distributed tracing (Jaeger)
- [ ] Set up log aggregation (Loki)
- [ ] Create custom alerts for cost anomalies

### High Availability

- [ ] Enable multi-AZ deployment (set `enable_multi_az=true`)
- [ ] Configure RDS read replicas
- [ ] Set up Redis cluster mode
- [ ] Configure HPA for all services
- [ ] Test failover scenarios
- [ ] Set up automated backups

### Performance

- [ ] Enable TimescaleDB continuous aggregates
- [ ] Configure Redis cache TTLs
- [ ] Optimize database indexes
- [ ] Enable CDN for frontend (CloudFront/Cloud CDN)
- [ ] Configure connection pooling

## Configuration Options

### Helm Values

Edit `k8s/helm/afoc/values.yaml`:

```yaml
# Production configuration
metricsCollector:
  replicaCount: 5
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
    limits:
      memory: "1Gi"
      cpu: "1000m"

mlEngine:
  replicaCount: 3
  resources:
    requests:
      memory: "4Gi"  # ML models need more memory
      cpu: "2000m"

# Enable auto-scaling
metricsCollector:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
```

### Terraform Variables

Create `terraform/terraform.tfvars`:

```hcl
environment          = "prod"
aws_region           = "us-east-1"
gcp_project_id       = "your-project-id"
azure_subscription_id = "your-subscription-id"

db_instance_class    = "db.r6g.xlarge"  # Production instance
enable_multi_az      = true

# Network configuration
vpc_cidr             = "10.0.0.0/16"

# Scaling
eks_node_min_size    = 3
eks_node_max_size    = 20
eks_node_instance_type = "t3.xlarge"
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod -n afoc <pod-name>

# Check logs
kubectl logs -n afoc <pod-name> --previous

# Common issues:
# 1. Image pull errors: Check image registry credentials
# 2. Insufficient resources: Check node capacity
# 3. ConfigMap/Secret missing: Verify Helm values
```

### Database Connection Errors

```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h <RDS_ENDPOINT> -U afoc -d afoc

# Check database credentials
kubectl get secret -n afoc afoc-postgresql -o jsonpath='{.data.password}' | base64 -d
```

### Performance Issues

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n afoc

# Scale up if needed
kubectl scale deployment -n afoc afoc-metrics-collector --replicas=10

# Check HPA status
kubectl get hpa -n afoc
```

## Maintenance

### Updating AFOC

```bash
# Pull latest changes
git pull origin main

# Update Terraform infrastructure
cd terraform/
terraform plan
terraform apply

# Update Helm deployment
cd ../k8s/
helm upgrade afoc ./helm/afoc --namespace afoc
```

### Backup & Restore

**Database Backup**:
```bash
# RDS automated backups are enabled by default
# Manual snapshot:
aws rds create-db-snapshot \
  --db-instance-identifier afoc-postgres-prod \
  --db-snapshot-identifier afoc-manual-backup-$(date +%Y%m%d)
```

**Restore from Backup**:
```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier afoc-postgres-restored \
  --db-snapshot-identifier afoc-manual-backup-20250107
```

## Monitoring Endpoints

- **Prometheus**: `kubectl port-forward -n afoc svc/prometheus-server 9090:80`
- **Grafana**: `kubectl port-forward -n afoc svc/grafana 3000:80`
- **Jaeger**: `kubectl port-forward -n afoc svc/jaeger-query 16686:16686`

Default Credentials:
- Grafana: `admin` / (check Helm values)

## Cost Optimization

### Expected Costs (Monthly)

**AWS (us-east-1)**:
- EKS cluster: $73 (control plane)
- EC2 nodes (3x t3.large): $150
- RDS PostgreSQL (db.t3.medium): $120
- ElastiCache Redis: $50
- Data transfer: ~$30
- **Total**: ~$423/month

**Cost Savings**:
- AFOC will typically save 20-30% of your cloud costs
- Break-even at ~$1,500/month cloud spend
- ROI increases with scale

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/afoc/issues
- Slack: #afoc-platform
- Email: platform-team@afoc.io

---

**Document Version**: 1.0.0
**Last Updated**: 2025-01-07
