#!/usr/bin/env python3
"""
S3 버킷에 설정 파일 및 문서를 업로드하는 스크립트
Terraform으로 S3 버킷 생성 후 실행
"""

import boto3
import json
import os
import sys
from pathlib import Path

# AWS 리전 설정
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')

# S3 클라이언트 생성
s3 = boto3.client('s3', region_name=AWS_REGION)


def upload_file_to_s3(bucket_name: str, local_path: str, s3_key: str, content_type: str = None) -> bool:
    """로컬 파일을 S3에 업로드"""
    try:
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        s3.upload_file(local_path, bucket_name, s3_key, ExtraArgs=extra_args)
        print(f"  ✅ Uploaded: {s3_key}")
        return True
    except FileNotFoundError:
        print(f"  ⚠️  File not found: {local_path}")
        return False
    except Exception as e:
        print(f"  ❌ Failed to upload {s3_key}: {e}")
        return False


def upload_string_to_s3(bucket_name: str, content: str, s3_key: str, content_type: str = 'text/plain') -> bool:
    """문자열을 S3에 업로드"""
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=content.encode('utf-8'),
            ContentType=content_type
        )
        print(f"  ✅ Uploaded: {s3_key}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to upload {s3_key}: {e}")
        return False


def upload_config_json(bucket_name: str) -> None:
    """설정 JSON 파일 업로드"""
    print("\n📤 Uploading configuration files...")
    
    # 설정 파일 경로
    config_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data',
        'config',
        'production.json'
    )
    
    if os.path.exists(config_file):
        upload_file_to_s3(
            bucket_name,
            config_file,
            'config/production.json',
            'application/json'
        )
    else:
        # 기본 설정 생성 및 업로드
        default_config = {
            'JWT_SECRET': os.getenv('JWT_SECRET', 'your-super-secret-jwt-key'),
            'AWS_REGION': AWS_REGION,
            'NODE_ENV': 'production',
            'JWT_ACCESS_EXPIRES_IN': '15m',
            'JWT_REFRESH_EXPIRES_IN': '7d'
        }
        upload_string_to_s3(
            bucket_name,
            json.dumps(default_config, indent=2),
            'config/production.json',
            'application/json'
        )


def upload_documentation(bucket_name: str) -> None:
    """문서 파일 업로드"""
    print("\n📚 Uploading documentation...")
    
    project_root = Path(__file__).parent.parent
    docs_dir = project_root / 'docs'
    
    # API.md 업로드
    api_doc = docs_dir / 'API.md'
    if api_doc.exists():
        upload_file_to_s3(
            bucket_name,
            str(api_doc),
            'docs/API.md',
            'text/markdown'
        )
    
    # DEPLOYMENT.md 업로드
    deployment_doc = docs_dir / 'DEPLOYMENT.md'
    if deployment_doc.exists():
        upload_file_to_s3(
            bucket_name,
            str(deployment_doc),
            'docs/DEPLOYMENT.md',
            'text/markdown'
        )


def upload_env_example(bucket_name: str) -> None:
    """env.example 파일 업로드"""
    print("\n📝 Uploading environment example...")
    
    env_example = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'env.example'
    )
    
    if os.path.exists(env_example):
        upload_file_to_s3(
            bucket_name,
            env_example,
            'config/env.example',
            'text/plain'
        )


def main():
    """메인 함수"""
    print("🚀 Starting S3 file upload...")
    
    # Terraform output에서 버킷명 가져오기 (환경 변수 또는 직접 지정)
    bucket_name = os.getenv('S3_BUCKET_NAME', '')
    
    if not bucket_name:
        print("❌ S3_BUCKET_NAME environment variable is required")
        print("   Set it from Terraform output: terraform output -raw s3_bucket_name")
        sys.exit(1)
    
    print(f"📦 Target bucket: {bucket_name}")
    
    # 버킷 존재 확인
    try:
        s3.head_bucket(Bucket=bucket_name)
    except Exception as e:
        print(f"❌ Cannot access bucket {bucket_name}: {e}")
        sys.exit(1)
    
    # 파일 업로드
    upload_config_json(bucket_name)
    upload_documentation(bucket_name)
    upload_env_example(bucket_name)
    
    print("\n✅ File upload completed!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

