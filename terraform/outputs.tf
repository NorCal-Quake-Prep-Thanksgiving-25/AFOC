output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}
