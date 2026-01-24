# API Gateway - 기존 엔드포인트 유지하면서 Kubernetes 백엔드 연결

# 기존 API Gateway 찾기 (선택사항 - 기존 API Gateway가 있다면)
# 주석을 해제하고 기존 API Gateway 이름을 입력하세요
variable "existing_api_gateway_name" {
  description = "기존 API Gateway 이름 (있는 경우)"
  type        = string
  default     = ""
}

# 기존 API Gateway 찾기 (ID 또는 이름으로)
# 주의: existing_api_gateway_name에는 API Gateway ID를 입력해야 합니다
data "aws_apigatewayv2_api" "existing" {
  count = var.existing_api_gateway_name != "" ? 1 : 0
  api_id = var.existing_api_gateway_name
}

# 기존 API Gateway 사용 여부
locals {
  use_existing_api = var.existing_api_gateway_name != ""
}

# API Gateway V2 (HTTP API) 생성 (기존 것이 없을 때만)
resource "aws_apigatewayv2_api" "authcore" {
  count = local.use_existing_api ? 0 : 1
  
  name          = "authcore-api-${var.environment}"
  protocol_type = "HTTP"
  description   = "AuthCore API Gateway - Kubernetes Backend"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["*"]
    max_age       = 300
  }

  tags = {
    Name        = "authcore-api-${var.environment}"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "prod" {
  count  = local.use_existing_api ? 0 : 1
  api_id = aws_apigatewayv2_api.authcore[0].id
  name   = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_rate_limit  = 100
    throttling_burst_limit = 200
  }

  tags = {
    Name        = "authcore-api-stage-${var.environment}"
    Environment = var.environment
  }
}

# API Gateway ID (기존 또는 새로 생성된 것)
locals {
  api_gateway_id = local.use_existing_api ? var.existing_api_gateway_name : aws_apigatewayv2_api.authcore[0].id
}

# 참고: Integration과 Route는 Kubernetes 배포 후
# scripts/update_apigateway_backend.py 스크립트로 생성/업데이트됩니다.
# 이는 LoadBalancer URL이 배포 후에만 알 수 있기 때문입니다.

# API Gateway 출력값
output "api_gateway_url" {
  description = "API Gateway 엔드포인트 URL"
  value       = local.use_existing_api ? "기존 API Gateway 사용 중" : aws_apigatewayv2_api.authcore[0].api_endpoint
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = local.api_gateway_id
}

output "api_gateway_integration_note" {
  description = "API Gateway Integration 설정 안내"
  value       = "Kubernetes 배포 후 'python scripts/update_apigateway_backend.py' 실행하여 백엔드 연결"
}
