# Secrets Manager - JWT Secret (컨테이너만 Terraform이 생성)
# 시크릿 값은 AWS 콘솔/CLI에서 한 번 설정하고, 이후 로테이션 등은 Secrets Manager에서 관리
resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "authcore/jwt-secret-${var.environment}"
  description = "JWT Secret Key for AuthCore (값은 콘솔/CLI에서 설정)"

  tags = {
    Name = "AuthCore JWT Secret"
  }
}

# 시크릿 값은 Terraform이 넣지 않음 → 콘솔에서 "Store a new secret value" 또는
#   aws secretsmanager put-secret-value --secret-id authcore/jwt-secret-prod --secret-string "YOUR_JWT_VALUE"
# 기존에 Terraform이 secret_version을 관리했다면, apply 전에 state에서만 제거 (AWS 값은 유지):
#   terraform state rm 'aws_secretsmanager_secret_version.jwt_secret'
# 로테이션은 lambda_rotation.tf의 커스텀 Lambda로 N일마다 자동 수행됨 (jwt_rotation_days 변수).

