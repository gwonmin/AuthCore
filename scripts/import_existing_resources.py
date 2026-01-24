#!/usr/bin/env python3
"""
기존 AWS 리소스를 Terraform state로 import하는 스크립트
"""

import os
import sys
import subprocess
import boto3
from pathlib import Path

# 색상 출력
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.NC}")

def print_info(msg):
    print(f"{Colors.YELLOW}📋 {msg}{Colors.NC}")

def print_step(msg):
    print(f"{Colors.BLUE}🚀 {msg}{Colors.NC}")

def run_command(cmd, check=True, cwd=None, capture_output=True):
    """명령어 실행"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            cwd=cwd,
            capture_output=capture_output,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout if hasattr(e, 'stdout') else '', str(e)

def check_table_exists(table_name: str, region: str = 'ap-northeast-2') -> bool:
    """DynamoDB 테이블 존재 확인"""
    try:
        dynamodb = boto3.client('dynamodb', region_name=region)
        dynamodb.describe_table(TableName=table_name)
        return True
    except dynamodb.exceptions.ResourceNotFoundException:
        return False
    except Exception as e:
        print_error(f"Error checking table {table_name}: {e}")
        return False

def check_terraform_state(resource_address: str, terraform_dir: Path) -> bool:
    """Terraform state에 리소스가 있는지 확인"""
    success, stdout, stderr = run_command(
        f"terraform state show {resource_address}",
        check=False,
        cwd=str(terraform_dir),
        capture_output=True
    )
    return success

def import_dynamodb_table(table_name: str, resource_address: str, terraform_dir: Path) -> bool:
    """DynamoDB 테이블을 Terraform state로 import"""
    print_info(f"  Importing to Terraform state...")
    
    success, stdout, stderr = run_command(
        f"terraform import {resource_address} {table_name}",
        check=False,
        cwd=str(terraform_dir),
        capture_output=True
    )
    
    if success:
        print_success(f"  ✅ {table_name} imported")
        return True
    else:
        print_error(f"  ❌ Failed to import {table_name}: {stderr}")
        return False

def main():
    """메인 함수"""
    print("=" * 60)
    print("📥 기존 AWS 리소스 Import 스크립트")
    print("=" * 60)
    print()
    
    # 경로 설정
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    terraform_dir = project_root / 'terraform'
    
    if not terraform_dir.exists():
        print_error(f"Terraform directory not found: {terraform_dir}")
        sys.exit(1)
    
    # AWS 리전 확인
    aws_region = os.getenv('AWS_REGION', 'ap-northeast-2')
    print_info(f"AWS Region: {aws_region}")
    print()
    
    # Terraform 초기화 확인
    if not (terraform_dir / '.terraform').exists():
        print_info("Terraform not initialized. Running 'terraform init'...")
        success, stdout, stderr = run_command(
            "terraform init",
            check=False,
            cwd=str(terraform_dir),
            capture_output=False
        )
        if not success:
            print_error("Failed to initialize Terraform")
            sys.exit(1)
        print()
    
    # DynamoDB 테이블 import
    print_step("Step 1: Importing DynamoDB tables...")
    
    tables_to_import = [
        {
            'name': 'AuthCore_Users',
            'resource': 'aws_dynamodb_table.users'
        },
        {
            'name': 'AuthCore_RefreshTokens',
            'resource': 'aws_dynamodb_table.refresh_tokens'
        }
    ]
    
    imported_count = 0
    skipped_count = 0
    
    for table in tables_to_import:
        table_name = table['name']
        resource_address = table['resource']
        
        if check_table_exists(table_name, aws_region):
            print_info(f"Found existing table: {table_name}")
            
            if check_terraform_state(resource_address, terraform_dir):
                print_info("  Already in Terraform state, skipping...")
                skipped_count += 1
            else:
                if import_dynamodb_table(table_name, resource_address, terraform_dir):
                    imported_count += 1
        else:
            print_info(f"  Table {table_name} does not exist, will be created")
    
    print()
    
    if imported_count > 0:
        print_success(f"Import completed! ({imported_count} table(s) imported)")
    elif skipped_count > 0:
        print_success(f"All tables already in Terraform state ({skipped_count} table(s))")
    else:
        print_info("No existing tables found. They will be created by Terraform.")
    
    print()
    print_info("Next steps:")
    print("  1. Run 'terraform plan' to verify the import")
    print("  2. Run 'terraform apply' to sync any differences")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
