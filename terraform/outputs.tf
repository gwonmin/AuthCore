output "users_table_name" {
  description = "DynamoDB Users 테이블 이름"
  value       = aws_dynamodb_table.users.name
}

output "refresh_tokens_table_name" {
  description = "DynamoDB RefreshTokens 테이블 이름"
  value       = aws_dynamodb_table.refresh_tokens.name
}

output "s3_bucket_name" {
  description = "S3 버킷 이름"
  value       = aws_s3_bucket.config.id
}

output "s3_bucket_arn" {
  description = "S3 버킷 ARN"
  value       = aws_s3_bucket.config.arn
}

output "secrets_manager_arn" {
  description = "Secrets Manager ARN"
  value       = aws_secretsmanager_secret.jwt_secret.arn
  sensitive   = true
}

# EC2 및 Kubernetes 관련 출력값
output "ec2_instance_id" {
  description = "EC2 인스턴스 ID"
  value       = aws_instance.k8s_node.id
}

output "ec2_public_ip" {
  description = "EC2 인스턴스 Public IP"
  value       = aws_instance.k8s_node.public_ip
}

output "ec2_elastic_ip" {
  description = "EC2 인스턴스 Elastic IP"
  value       = aws_eip.k8s_node.public_ip
}

output "ec2_ssh_command" {
  description = "EC2 인스턴스 SSH 접속 명령어"
  value       = "ssh -i ~/.ssh/your-key.pem ubuntu@${aws_instance.k8s_node.public_ip}"
}

output "ecr_repository_url" {
  description = "ECR 리포지토리 URL"
  value       = aws_ecr_repository.authcore.repository_url
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

