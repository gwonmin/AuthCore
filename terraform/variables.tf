variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "환경 이름 (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "jwt_secret" {
  description = "JWT Secret Key (Secrets Manager에 저장됨)"
  type        = string
  sensitive   = true
  default     = "your-super-secret-jwt-key-change-this-in-production"
}

variable "dynamodb_read_capacity" {
  description = "DynamoDB 읽기 용량"
  type        = number
  default     = 5
}

variable "dynamodb_write_capacity" {
  description = "DynamoDB 쓰기 용량"
  type        = number
  default     = 5
}

variable "s3_bucket_name" {
  description = "S3 버킷 이름 (고유해야 함)"
  type        = string
  default     = ""
}

variable "key_pair_name" {
  description = "EC2 키 페어 이름 (SSH 접속용, 선택사항)"
  type        = string
  default     = ""
}

variable "ec2_instance_type" {
  description = "EC2 인스턴스 타입 (권장: t3.medium 이상, 최소: t3.small)"
  type        = string
  default     = "t3.small"
}
