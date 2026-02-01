# JWT 시크릿 자동 로테이션 - 커스텀 Lambda
# Secrets Manager는 단순 문자열 시크릿에 대한 기본 로테이션이 없어, Lambda로 create_secret/finish_secret 처리

locals {
  lambda_rotation_source_dir = "${path.module}/lambda/jwt_rotation"
}

# Lambda 배포 패키지 (zip)
data "archive_file" "jwt_rotation" {
  type        = "zip"
  source_dir  = local.lambda_rotation_source_dir
  output_path = "${path.module}/jwt_rotation.zip"
}

# Lambda 실행 역할
resource "aws_iam_role" "jwt_rotation_lambda" {
  name = "authcore-jwt-rotation-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Lambda: CloudWatch Logs + Secrets Manager (해당 시크릿만)
resource "aws_iam_role_policy" "jwt_rotation_lambda" {
  name   = "jwt-rotation-policy"
  role   = aws_iam_role.jwt_rotation_lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue", "secretsmanager:PutSecretValue", "secretsmanager:DescribeSecret", "secretsmanager:UpdateSecretVersionStage"]
        Resource = aws_secretsmanager_secret.jwt_secret.arn
      }
    ]
  })
}

# Lambda 함수
resource "aws_lambda_function" "jwt_rotation" {
  filename         = data.archive_file.jwt_rotation.output_path
  function_name    = "authcore-jwt-rotation-${var.environment}"
  role             = aws_iam_role.jwt_rotation_lambda.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.jwt_rotation.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {}
  }
}

# Secrets Manager가 이 시크릿 로테이션 시에만 Lambda를 호출할 수 있도록 권한 (source_arn으로 제한)
resource "aws_lambda_permission" "secrets_manager_invoke" {
  statement_id  = "AllowExecutionFromSecretsManager"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.jwt_rotation.function_name
  principal     = "secretsmanager.amazonaws.com"
  source_arn    = aws_secretsmanager_secret.jwt_secret.arn
}

# 시크릿 로테이션 설정 (N일마다 자동 로테이션)
resource "aws_secretsmanager_secret_rotation" "jwt_secret" {
  secret_id           = aws_secretsmanager_secret.jwt_secret.id
  rotation_lambda_arn = aws_lambda_function.jwt_rotation.arn

  rotation_rules {
    automatically_after_days = var.jwt_rotation_days
  }

  depends_on = [aws_lambda_permission.secrets_manager_invoke]
}
