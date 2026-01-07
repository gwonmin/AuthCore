# ECR 리포지토리
resource "aws_ecr_repository" "authcore" {
  name                 = "authcore-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "AuthCore ECR Repository"
  }
}

# ECR 생명주기 정책 (이미지 보관 정책)
resource "aws_ecr_lifecycle_policy" "authcore" {
  repository = aws_ecr_repository.authcore.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

