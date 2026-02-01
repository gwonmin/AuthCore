#!/usr/bin/env python3
"""
EC2에서 kubeconfig를 복사하여 로컬 Kubernetes 접근 설정
"""

import os
import subprocess
import sys
import tempfile
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

def run_command(cmd, check=True, env=None):
    """명령어 실행"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=check, 
            capture_output=True, 
            text=True,
            env=env if env else os.environ
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stdout if hasattr(e, 'stdout') else '', e.stderr if hasattr(e, 'stderr') else ''

def check_kubectl():
    """kubectl 설치 확인"""
    success, _, _ = run_command("kubectl version --client", check=False)
    return success

def verify_cluster(kubeconfig_path):
    """클러스터 연결 확인"""
    env = os.environ.copy()
    env['KUBECONFIG'] = kubeconfig_path
    
    success, output, _ = run_command("kubectl cluster-info", check=False, env=env)
    if success:
        print_success("Successfully connected to cluster!")
        # 환경 변수 전달하여 노드 확인
        success_nodes, output_nodes, _ = run_command("kubectl get nodes", check=False, env=env)
        if success_nodes:
            print_info(output_nodes)
        return True
    return False

def main():
    """메인 함수"""
    print("🚀 Setting up Kubernetes access...")
    
    # 환경 변수 설정
    ec2_ip = os.getenv('EC2_IP', '')
    ssh_key = os.getenv('SSH_KEY', os.path.expanduser('~/.ssh/id_rsa'))
    kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
    
    # EC2 IP 확인
    if not ec2_ip:
        print_info("EC2_IP not set")
        print_info("Get EC2 IP from Terraform output:")
        print("   terraform output -raw ec2_public_ip")
        print()
        ec2_ip = input("Enter EC2 Public IP: ").strip()
    
    if not ec2_ip:
        print_error("EC2 IP is required")
        sys.exit(1)
    
    # SSH 키 처리 (파일 경로 또는 키 내용)
    ssh_key_path = ssh_key
    temp_ssh_key = None
    
    # SSH 키가 파일 경로가 아닌 경우 (예: GitHub Actions secrets)
    if not os.path.exists(ssh_key):
        # 키 내용인지 확인 (-----BEGIN로 시작하는지)
        if ssh_key.startswith('-----BEGIN'):
            # 임시 파일로 저장
            temp_ssh_key = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
            temp_ssh_key.write(ssh_key)
            temp_ssh_key.close()
            ssh_key_path = temp_ssh_key.name
            os.chmod(ssh_key_path, 0o600)
            print_info("SSH key saved to temporary file")
        else:
            print_info(f"SSH key not found at {ssh_key}")
            ssh_key = input("Enter SSH key path: ").strip()
            if not os.path.exists(ssh_key):
                print_error(f"SSH key not found: {ssh_key}")
                sys.exit(1)
            ssh_key_path = ssh_key
    
    # kubeconfig 디렉토리 생성
    kubeconfig_dir = Path(kubeconfig_path).parent
    kubeconfig_dir.mkdir(parents=True, exist_ok=True)
    
    # EC2에서 kubeconfig 복사
    print_info("Copying kubeconfig from EC2...")
    scp_cmd = f"scp -o StrictHostKeyChecking=no -i {ssh_key_path} ubuntu@{ec2_ip}:/home/ubuntu/.kube/config {kubeconfig_path}"
    success, output, error = run_command(scp_cmd)
    
    if not success:
        # 임시 SSH 키 파일 정리
        if temp_ssh_key and os.path.exists(temp_ssh_key.name):
            try:
                os.unlink(temp_ssh_key.name)
            except Exception:
                pass
        print_error(f"Failed to copy kubeconfig: {error}")
        if output:
            print_error(f"Output: {output}")
        sys.exit(1)
    
    # 임시 SSH 키 파일 정리 (성공한 경우)
    if temp_ssh_key and os.path.exists(temp_ssh_key.name):
        try:
            os.unlink(temp_ssh_key.name)
        except Exception as e:
            print_error(f"Failed to remove temp SSH key file: {e}")
    
    # kubeconfig 권한 설정
    os.chmod(kubeconfig_path, 0o600)
    
    # 클러스터 연결 확인
    print_info("Verifying cluster connection...")
    if not verify_cluster(kubeconfig_path):
        print_error("Failed to connect to cluster")
        sys.exit(1)
    
    print_success("Kubernetes setup completed!")
    print_info(f"kubeconfig location: {kubeconfig_path}")
    print_info("To use kubectl, set:")
    print(f"   export KUBECONFIG={kubeconfig_path}")

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

