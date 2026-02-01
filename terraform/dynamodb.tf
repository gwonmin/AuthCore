# Users 테이블
resource "aws_dynamodb_table" "users" {
  name           = "AuthCore_Users"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "username"
    type = "S"
  }

  global_secondary_index {
    name            = "username-index"
    hash_key        = "username"
    projection_type = "ALL"
    read_capacity   = var.dynamodb_read_capacity
    write_capacity  = var.dynamodb_write_capacity
  }

  tags = {
    Name        = "AuthCore_Users"
    Description = "사용자 정보 저장 테이블"
  }

  # 기존 테이블 import 후 불필요한 변경 방지
  lifecycle {
    ignore_changes = [
      # 태그는 기존 것 유지 (default_tags와 충돌 방지)
      tags,
      tags_all,
      # DeletionProtection은 별도로 관리
      deletion_protection_enabled,
    ]
  }
}

# RefreshTokens 테이블
resource "aws_dynamodb_table" "refresh_tokens" {
  name           = "AuthCore_RefreshTokens"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "token_id"

  attribute {
    name = "token_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user-id-index"
    hash_key        = "user_id"
    projection_type = "ALL"
    read_capacity   = var.dynamodb_read_capacity
    write_capacity  = var.dynamodb_write_capacity
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name        = "AuthCore_RefreshTokens"
    Description = "리프레시 토큰 저장 테이블"
  }

  # 기존 테이블 import 후 불필요한 변경 방지
  lifecycle {
    ignore_changes = [
      # 태그는 기존 것 유지 (default_tags와 충돌 방지)
      tags,
      tags_all,
      # DeletionProtection은 별도로 관리
      deletion_protection_enabled,
    ]
  }
}

