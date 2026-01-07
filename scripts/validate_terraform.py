#!/usr/bin/env python3
"""
Terraform 파일 검증 스크립트
- terraform fmt: 포맷팅 검사
- terraform init: 초기화
- terraform validate: 문법 및 유효성 검사
"""

import os
import subprocess
import sys
from pathlib import Path

# 색상 출력
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.NC}")

def print_info(msg):
    print(f"{Colors.YELLOW}📋 {msg}{Colors.NC}")

def run_command(cmd, cwd=None, check=True):
    """명령어 실행"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stdout if hasattr(e, 'stdout') else '', e.stderr if hasattr(e, 'stderr') else ''

def check_terraform():
    """Terraform 설치 확인"""
    success, _, _ = run_command("terraform version", check=False)
    return success

def terraform_fmt_check(terraform_dir):
    """Terraform 포맷팅 검사"""
    print_info("Checking Terraform formatting...")
    success, output, error = run_command(
        "terraform fmt -check -recursive",
        cwd=terraform_dir,
        check=False
    )
    if success:
        print_success("Terraform formatting is correct")
        return True
    else:
        print_error("Terraform formatting issues found:")
        if output:
            print_error(output)
        if error:
            print_error(error)
        print_info("Run 'terraform fmt -recursive' to fix formatting")
        return False

def terraform_init(terraform_dir):
    """Terraform 초기화 (검증용)"""
    print_info("Initializing Terraform (validation only)...")
    success, output, error = run_command(
        "terraform init -backend=false",
        cwd=terraform_dir,
        check=False
    )
    if success:
        print_success("Terraform initialized successfully")
        return True
    else:
        print_error("Terraform initialization failed:")
        if error:
            print_error(error)
        return False

def terraform_validate(terraform_dir):
    """Terraform 유효성 검사"""
    print_info("Validating Terraform configuration...")
    success, output, error = run_command(
        "terraform validate",
        cwd=terraform_dir,
        check=False
    )
    if success:
        print_success("Terraform configuration is valid")
        if output:
            print_info(output)
        return True
    else:
        print_error("Terraform validation failed:")
        if error:
            print_error(error)
        if output:
            print_error(output)
        return False

def main():
    """메인 함수"""
    print("🔍 Validating Terraform files...")
    print("=" * 60)
    
    # Terraform 설치 확인
    if not check_terraform():
        print_error("Terraform is not installed")
        print_info("Install Terraform: https://www.terraform.io/downloads")
        sys.exit(1)
    
    # Terraform 디렉토리 찾기
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    terraform_dir = project_root / 'terraform'
    
    if not terraform_dir.exists():
        print_error(f"Terraform directory not found: {terraform_dir}")
        sys.exit(1)
    
    print_info(f"Terraform directory: {terraform_dir}")
    print()
    
    # 1. 포맷팅 검사
    fmt_ok = terraform_fmt_check(str(terraform_dir))
    print()
    
    # 2. 초기화
    init_ok = terraform_init(str(terraform_dir))
    print()
    
    if not init_ok:
        print_error("Cannot proceed with validation without initialization")
        sys.exit(1)
    
    # 3. 유효성 검사
    validate_ok = terraform_validate(str(terraform_dir))
    print()
    
    # 결과 요약
    print("=" * 60)
    if fmt_ok and init_ok and validate_ok:
        print_success("All Terraform checks passed!")
        sys.exit(0)
    else:
        print_error("Some Terraform checks failed")
        if not fmt_ok:
            print_error("  - Formatting issues")
        if not init_ok:
            print_error("  - Initialization failed")
        if not validate_ok:
            print_error("  - Validation failed")
        sys.exit(1)

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

