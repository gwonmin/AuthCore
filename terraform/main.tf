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

  # CI에서 plan/apply 사용 시 S3 백엔드 필요. bucket/key/region은 init 시 -backend-config로 전달
  # 로컬: terraform init -reconfigure -backend-config="bucket=YOUR_BUCKET" -backend-config="key=authcore/prod/terraform.tfstate" -backend-config="region=ap-northeast-2"
  backend "s3" {
    # partial config - CI/로컬 모두 init 시 -backend-config로 전달
  }
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

