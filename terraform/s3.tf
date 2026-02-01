# S3 버킷 이름 생성 (고유성 보장)
locals {
  s3_bucket_name = var.s3_bucket_name != "" ? var.s3_bucket_name : "authcore-config-${var.environment}-${random_id.bucket_suffix.hex}"
}

# 랜덤 ID 생성 (버킷 이름 고유성 보장)
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 버킷
resource "aws_s3_bucket" "config" {
  bucket = local.s3_bucket_name

  tags = {
    Name        = "AuthCore Config Bucket"
    Description = "설정 파일 및 문서 저장용 버킷"
  }
}

# 버킷 버전 관리
resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.id

  versioning_configuration {
    status = "Enabled"
  }
}

# 버킷 암호화
resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 퍼블릭 액세스 차단
resource "aws_s3_bucket_public_access_block" "config" {
  bucket = aws_s3_bucket.config.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 버킷 정책 (EC2/Kubernetes Pod에서 읽기만 허용)
resource "aws_s3_bucket_policy" "config" {
  bucket = aws_s3_bucket.config.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ec2_role.arn
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.config.arn,
          "${aws_s3_bucket.config.arn}/*"
        ]
      }
    ]
  })
}

