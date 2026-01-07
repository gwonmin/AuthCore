#!/usr/bin/env python3
"""
Docker 이미지를 빌드하고 ECR에 푸시하는 스크립트
"""

import os
import subprocess
import sys
import boto3

# 색상 출력
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.NC}")

def print_info(msg):
    print(f"{Colors.YELLOW}📋 {msg}{Colors.NC}")

def run_command(cmd, check=True):
    """명령어 실행"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {cmd}")
        print_error(e.stderr)
        sys.exit(1)

def get_aws_account_id():
    """AWS 계정 ID 가져오기"""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def ecr_login(region, repository_uri):
    """ECR에 로그인"""
    print_info("Logging in to ECR...")
    cmd = f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {repository_uri}"
    run_command(cmd)

def build_image(repo_name, tag):
    """Docker 이미지 빌드"""
    print_info("Building Docker image...")
    # 프로젝트 루트 디렉토리로 이동하여 빌드
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Dockerfile이 있는지 확인
    dockerfile_path = os.path.join(project_root, 'Dockerfile')
    if not os.path.exists(dockerfile_path):
        print_error(f"Dockerfile not found at {dockerfile_path}")
        sys.exit(1)
    
    cmd = f"docker build -t {repo_name}:{tag} ."
    # 프로젝트 루트에서 실행
    try:
        result = subprocess.run(cmd, shell=True, cwd=project_root, check=True, capture_output=True, text=True)
        print_success("Docker image built successfully")
        if result.stdout:
            print_info(result.stdout)
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {cmd}")
        if e.stderr:
            print_error(e.stderr)
        if e.stdout:
            print_error(e.stdout)
        sys.exit(1)

def tag_image(repo_name, tag, repository_uri):
    """Docker 이미지 태그"""
    cmd = f"docker tag {repo_name}:{tag} {repository_uri}:{tag}"
    run_command(cmd)

def push_image(repository_uri, tag):
    """ECR에 이미지 푸시"""
    print_info("Pushing image to ECR...")
    cmd = f"docker push {repository_uri}:{tag}"
    run_command(cmd)

def main():
    """메인 함수"""
    print("🚀 Building and pushing Docker image...")
    
    # 환경 변수 설정
    aws_region = os.getenv('AWS_REGION', 'ap-northeast-2')
    environment = os.getenv('ENVIRONMENT', 'prod')
    image_tag = os.getenv('IMAGE_TAG', 'latest')
    ecr_repo_name = f"authcore-{environment}"
    
    # AWS 계정 ID 가져오기
    try:
        aws_account_id = get_aws_account_id()
    except Exception as e:
        print_error(f"Failed to get AWS account ID: {e}")
        sys.exit(1)
    
    repository_uri = f"{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/{ecr_repo_name}"
    
    print_info("Configuration:")
    print(f"  AWS Region: {aws_region}")
    print(f"  ECR Repository: {ecr_repo_name}")
    print(f"  Image Tag: {image_tag}")
    print(f"  Repository URI: {repository_uri}")
    
    # ECR 로그인
    ecr_login(aws_region, repository_uri)
    
    # 이미지 빌드
    build_image(ecr_repo_name, image_tag)
    
    # 이미지 태그
    tag_image(ecr_repo_name, image_tag, repository_uri)
    
    # 이미지 푸시
    push_image(repository_uri, image_tag)
    
    print_success("Image pushed successfully!")
    print_success(f"Image URI: {repository_uri}:{image_tag}")
    
    # 이미지 URI를 파일에 저장 (프로젝트 루트에 저장)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    image_uri_file = os.path.join(project_root, '.image_uri')
    
    try:
        with open(image_uri_file, 'w', encoding='utf-8') as f:
            f.write(f"export IMAGE_URI={repository_uri}:{image_tag}\n")
        print_info(f"Image URI saved to {image_uri_file}")
    except Exception as e:
        print_error(f"Failed to save image URI to file: {e}")
        # 파일 저장 실패해도 계속 진행 (환경 변수로 전달 가능)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)

