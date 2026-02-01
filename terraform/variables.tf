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
  description = "JWT Secret - Terraform에서 Secrets Manager 값으로 쓰지 않음. 로컬/스크립트용으로만 사용 가능."
  type        = string
  sensitive   = true
  default     = ""
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

variable "jwt_rotation_days" {
  description = "JWT 시크릿 자동 로테이션 주기 (일). AWS 최소 1일."
  type        = number
  default     = 30

  validation {
    condition     = var.jwt_rotation_days >= 1
    error_message = "jwt_rotation_days must be at least 1."
  }
}
