#!/usr/bin/env python3
"""
환경 변수를 AWS Secrets Manager로 마이그레이션하는 스크립트
민감한 정보를 안전하게 관리
"""

import boto3
import os
import sys
import json

# AWS 리전 설정
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')

# Secrets Manager 클라이언트 생성
secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)


def load_env_file(file_path: str) -> dict:
    """.env 파일에서 환경 변수 로드"""
    env_vars = {}
    
    if not os.path.exists(file_path):
        print(f"⚠️  .env file not found: {file_path}")
        return env_vars
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
        
        return env_vars
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return {}


def get_secret(secret_name: str) -> dict:
    """Secrets Manager에서 시크릿 가져오기"""
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except secrets_client.exceptions.ResourceNotFoundException:
        return {}
    except Exception as e:
        print(f"⚠️  Error getting secret: {e}")
        return {}


def create_or_update_secret(secret_name: str, secret_value: dict, description: str = None) -> bool:
    """Secrets Manager에 시크릿 생성 또는 업데이트"""
    try:
        # 기존 시크릿 확인
        existing = get_secret(secret_name)
        
        if existing:
            # 업데이트
            print(f"  🔄 Updating existing secret: {secret_name}")
            secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_value, indent=2)
            )
        else:
            # 생성
            print(f"  ✨ Creating new secret: {secret_name}")
            secrets_client.create_secret(
                Name=secret_name,
                SecretString=json.dumps(secret_value, indent=2),
                Description=description or f"Configuration secrets for {secret_name}"
            )
        
        return True
    except Exception as e:
        print(f"  ❌ Error managing secret: {e}")
        return False


def main():
    """메인 함수"""
    print("🚀 Starting migration to AWS Secrets Manager...")
    
    # Secret 이름 (환경 변수 또는 기본값)
    secret_name = os.getenv('SECRETS_MANAGER_NAME', 'authcore/config-prod')
    
    # .env 파일 경로
    env_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        '.env'
    )
    
    # .env 파일에서 환경 변수 로드
    print(f"\n📖 Loading environment variables from {env_file}...")
    env_vars = load_env_file(env_file)
    
    if not env_vars:
        print("⚠️  No environment variables found in .env file")
        return
    
    print(f"  Found {len(env_vars)} environment variables")
    
    # 민감한 정보만 필터링 (선택사항)
    sensitive_keys = ['JWT_SECRET', 'AWS_SECRET_ACCESS_KEY', 'DATABASE_PASSWORD']
    sensitive_vars = {k: v for k, v in env_vars.items() if k in sensitive_keys}
    
    if not sensitive_vars:
        # 모든 변수를 저장하거나, 특정 키만 저장
        print("\n📝 Storing all environment variables...")
        secrets_to_store = env_vars
    else:
        print("\n🔐 Storing sensitive environment variables...")
        secrets_to_store = sensitive_vars
    
    # Secrets Manager에 저장
    print(f"\n💾 Saving to Secrets Manager: {secret_name}...")
    if create_or_update_secret(
        secret_name,
        secrets_to_store,
        "AuthCore configuration secrets"
    ):
        print("\n✅ Secrets migrated successfully!")
        print(f"\n📝 Stored variables:")
        for key in sorted(secrets_to_store.keys()):
            # 값은 마스킹
            value = secrets_to_store[key]
            masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '****'
            print(f"  - {key}: {masked_value}")
        
        print(f"\n💡 To retrieve secrets in Lambda:")
        print(f"   import boto3")
        print(f"   secrets = boto3.client('secretsmanager')")
        print(f"   response = secrets.get_secret_value(SecretId='{secret_name}')")
        print(f"   config = json.loads(response['SecretString'])")
    else:
        print("\n❌ Failed to migrate secrets")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

