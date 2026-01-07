terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Terraform State 저장소 (선택사항 - S3 백엔드 사용 시)
  # backend "s3" {
  #   bucket = "authcore-terraform-state"
  #   key    = "terraform.tfstate"
  #   region = "ap-northeast-2"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AuthCore"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

