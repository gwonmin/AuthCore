# Secrets Manager - JWT Secret
resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "authcore/jwt-secret-${var.environment}"
  description = "JWT Secret Key for AuthCore"

  tags = {
    Name = "AuthCore JWT Secret"
  }
}

# Secrets Manager Secret 값
resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret
}

# Secrets Manager 자동 로테이션 (선택사항)
# resource "aws_secretsmanager_secret_rotation" "jwt_secret" {
#   secret_id           = aws_secretsmanager_secret.jwt_secret.id
#   rotation_lambda_arn = aws_lambda_function.rotation.arn
#
#   rotation_rules {
#     automatically_after_days = 30
#   }
# }

