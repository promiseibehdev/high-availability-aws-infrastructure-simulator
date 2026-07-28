output "vpc_id" {
  description = "Example VPC identifier."
  value       = aws_vpc.main.id
}

output "load_balancer_dns_name" {
  description = "Example public ALB DNS name."
  value       = aws_lb.app.dns_name
}

output "private_subnet_ids" {
  description = "Private subnet identifiers used by Auto Scaling."
  value       = values(aws_subnet.private)[*].id
}

output "artifact_bucket_name" {
  description = "Private artifact bucket name."
  value       = aws_s3_bucket.artifacts.id
}
