#!/usr/bin/env python3
"""
Terraform 적용 후 자동으로 실행되는 통합 설정 스크립트
1. DynamoDB 테이블 활성화 대기
2. Seed 데이터 삽입
3. S3에 설정 파일 업로드
4. 환경 변수 마이그레이션 (선택사항)
"""

import subprocess
import json
import boto3
import time
import os
import sys

# AWS 리전 설정
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')

# DynamoDB 클라이언트
dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)


def get_terraform_outputs(terraform_dir: str = 'terraform') -> dict:
    """Terraform output 값 가져오기"""
    # 스크립트 디렉토리 기준으로 terraform 디렉토리 찾기
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    terraform_path = os.path.join(project_root, terraform_dir)
    
    if not os.path.exists(terraform_path):
        print(f"⚠️  Terraform directory not found: {terraform_path}")
        return {}
    
    try:
        result = subprocess.run(
            ['terraform', 'output', '-json'],
            capture_output=True,
            text=True,
            cwd=terraform_path,
            check=True
        )
        
        outputs = json.loads(result.stdout)
        # Terraform output 형식 변환
        return {k: v.get('value', '') for k, v in outputs.items()}
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to get Terraform outputs: {e.stderr}")
        return {}
    except FileNotFoundError:
        print("⚠️  Terraform not found. Make sure Terraform is installed.")
        return {}
    except json.JSONDecodeError:
        print("⚠️  Failed to parse Terraform outputs")
        return {}


def wait_for_table_active(table_name: str, max_wait: int = 300) -> bool:
    """DynamoDB 테이블이 활성화될 때까지 대기"""
    print(f"\n⏳ Waiting for DynamoDB table '{table_name}' to be ACTIVE...")
    
    start_time = time.time()
    
    while True:
        try:
            response = dynamodb.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            
            if status == 'ACTIVE':
                elapsed = int(time.time() - start_time)
                print(f"  ✅ Table '{table_name}' is ACTIVE (took {elapsed}s)")
                return True
            
            elapsed = int(time.time() - start_time)
            if elapsed > max_wait:
                print(f"  ❌ Timeout waiting for table '{table_name}'")
                return False
            
            print(f"  ⏳ Status: {status} (elapsed: {elapsed}s)")
            time.sleep(5)
            
        except dynamodb.exceptions.ResourceNotFoundException:
            print(f"  ⚠️  Table '{table_name}' not found yet...")
            time.sleep(5)
        except Exception as e:
            print(f"  ❌ Error checking table status: {e}")
            return False


def run_script(script_name: str, env_vars: dict = None) -> bool:
    """Python 스크립트 실행"""
    # 스크립트 디렉토리 찾기 (현재 스크립트의 디렉토리)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    if not os.path.exists(script_path):
        print(f"⚠️  Script not found: {script_path}")
        return False
    
    print(f"\n🚀 Running {script_name}...")
    
    # 환경 변수 설정
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    # 프로젝트 루트 디렉토리로 이동하여 실행
    project_root = os.path.dirname(script_dir)
    
    try:
        result = subprocess.run(
            ['python3', script_path],
            env=env,
            check=True,
            cwd=project_root
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Script failed: {e}")
        return False
    except FileNotFoundError:
        # python3가 없으면 python 시도
        try:
            result = subprocess.run(
                ['python', script_path],
                env=env,
                check=True,
                cwd=project_root
            )
            return result.returncode == 0
        except Exception as e:
            print(f"  ❌ Script failed: {e}")
            return False


def main():
    """메인 함수"""
    print("=" * 60)
    print("🚀 Post-Terraform Setup Script")
    print("=" * 60)
    
    # 1. Terraform outputs 가져오기
    print("\n📋 Step 1: Getting Terraform outputs...")
    outputs = get_terraform_outputs()
    
    if not outputs:
        print("⚠️  Could not get Terraform outputs. Using default values...")
        outputs = {
            'users_table_name': 'AuthCore_Users',
            'refresh_tokens_table_name': 'AuthCore_RefreshTokens',
            's3_bucket_name': ''
        }
    else:
        print("  ✅ Got Terraform outputs")
        for key, value in outputs.items():
            if 'secret' not in key.lower() and 'arn' not in key.lower():
                print(f"    - {key}: {value}")
    
    # 2. DynamoDB 테이블 활성화 대기
    print("\n📋 Step 2: Waiting for DynamoDB tables...")
    users_table = outputs.get('users_table_name', 'AuthCore_Users')
    tokens_table = outputs.get('refresh_tokens_table_name', 'AuthCore_RefreshTokens')
    
    if not wait_for_table_active(users_table):
        print("❌ Users table is not ready")
        sys.exit(1)
    
    if not wait_for_table_active(tokens_table):
        print("❌ RefreshTokens table is not ready")
        sys.exit(1)
    
    # 3. Seed 데이터 삽입
    print("\n📋 Step 3: Seeding initial data...")
    seed_env = {
        'AWS_REGION': AWS_REGION,
        'USERS_TABLE_NAME': users_table,
        'REFRESH_TOKENS_TABLE_NAME': tokens_table
    }
    if not run_script('seed_data.py', seed_env):
        print("⚠️  Seed data script failed, but continuing...")
        # 실패해도 계속 진행 (선택사항이므로)
    
    # 4. S3에 설정 파일 업로드
    s3_bucket = outputs.get('s3_bucket_name', '')
    if s3_bucket:
        print("\n📋 Step 4: Uploading files to S3...")
        upload_env = {
            'AWS_REGION': AWS_REGION,
            'S3_BUCKET_NAME': s3_bucket
        }
        if not run_script('upload_config.py', upload_env):
            print("⚠️  S3 upload script failed, but continuing...")
            # 실패해도 계속 진행 (선택사항이므로)
    else:
        print("\n⚠️  Step 4: Skipping S3 upload (bucket name not found)")
    
    # 5. Kubernetes 배포 안내
    print("\n📋 Step 5: Kubernetes deployment")
    print("  💡 Next steps for Kubernetes deployment:")
    print("     1. Build and push Docker image: python scripts/build_and_push.py")
    print("     2. Setup kubeconfig: python scripts/setup_k8s.py")
    print("     3. Deploy to Kubernetes: python scripts/deploy_to_k8s.py")
    
    # 완료
    print("\n" + "=" * 60)
    print("✅ Post-Terraform setup completed!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("  1. Build and push Docker image: python scripts/build_and_push.py")
    print("  2. Setup kubeconfig: python scripts/setup_k8s.py")
    print("  3. Deploy to Kubernetes: python scripts/deploy_to_k8s.py")
    print("  4. Verify DynamoDB tables have seed data")
    if s3_bucket:
        print(f"  5. Check S3 bucket: {s3_bucket}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

