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

def _rewrite_kubeconfig_server(kubeconfig_path: str, server_ip: str, port: int = 6443):
    """kubeconfig의 server 주소를 지정 IP로 변경 (EC2에서 복사한 k3s 설정은 127.0.0.1이라 CI에서 접근 불가)"""
    import re
    with open(kubeconfig_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # server: https://127.0.0.1:6443 또는 https://10.x.x.x:6443 등 → https://<server_ip>:6443
    new_server = f"https://{server_ip}:{port}"
    content = re.sub(r'server:\s*https://[^:\s]+:\d+', f'server: {new_server}', content)
    with open(kubeconfig_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print_info(f"Kubeconfig server set to {new_server}")


def verify_cluster(kubeconfig_path):
    """클러스터 연결 확인"""
    env = os.environ.copy()
    env['KUBECONFIG'] = os.path.expanduser(kubeconfig_path) if isinstance(kubeconfig_path, str) else kubeconfig_path
    
    success, output, err = run_command("kubectl cluster-info", check=False, env=env)
    if success:
        print_success("Successfully connected to cluster!")
        # 환경 변수 전달하여 노드 확인
        success_nodes, output_nodes, _ = run_command("kubectl get nodes", check=False, env=env)
        if success_nodes:
            print_info(output_nodes)
        return True
    if err:
        print_error(err)
    return False

def main():
    """메인 함수"""
    print("🚀 Setting up Kubernetes access...")
    
    # 환경 변수 설정
    ec2_ip = os.getenv('EC2_IP', '')
    ssh_key = os.getenv('SSH_KEY', os.path.expanduser('~/.ssh/id_rsa'))
    kubeconfig_path = os.path.expanduser(os.getenv('KUBECONFIG', '~/.kube/config'))
    
    # EC2 IP 확인
    if not ec2_ip:
        if not os.isatty(0):
            print_error("EC2_IP is required (CI: set EC2_PUBLIC_IP in Get infrastructure values step)")
            sys.exit(1)
        print_info("EC2_IP not set")
        print_info("Get EC2 IP from AWS Console or cluster-infra terraform output")
        print()
        ec2_ip = input("Enter EC2 Public IP: ").strip()
    
    if not ec2_ip:
        print_error("EC2 IP is required")
        sys.exit(1)
    
    # SSH 키 처리 (파일 경로 또는 키 내용)
    ssh_key_path = ssh_key
    temp_ssh_key = None
    
    # 경로인 경우 ~ 확장 (CI에서 SSH_KEY=~/.ssh/id_rsa 로 넘길 때 필요)
    ssh_key_expanded = os.path.expanduser(ssh_key) if isinstance(ssh_key, str) and not ssh_key.startswith('-----BEGIN') else ssh_key
    
    # SSH 키가 파일 경로가 아닌 경우 (예: GitHub Actions에서 경로 전달 시 파일 있음, 키 내용 전달 시 BEGIN으로 시작)
    if ssh_key.startswith('-----BEGIN'):
        # 키 내용이 env로 직접 전달된 경우
        temp_ssh_key = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
        temp_ssh_key.write(ssh_key)
        temp_ssh_key.close()
        ssh_key_path = temp_ssh_key.name
        os.chmod(ssh_key_path, 0o600)
        print_info("SSH key saved to temporary file")
    elif os.path.exists(ssh_key_expanded):
        ssh_key_path = ssh_key_expanded
    else:
        # 파일 경로였는데 없음 → CI가 아닐 때만 입력 요청
        if os.isatty(0):
            print_info(f"SSH key not found at {ssh_key_expanded}")
            ssh_key = input("Enter SSH key path: ").strip()
            ssh_key_path = os.path.expanduser(ssh_key) if ssh_key else ""
            if not ssh_key_path or not os.path.exists(ssh_key_path):
                print_error(f"SSH key not found: {ssh_key_path or ssh_key}")
                sys.exit(1)
        else:
            print_error(f"SSH key not found at {ssh_key_expanded} (CI: ensure Setup SSH key step wrote to this path)")
            sys.exit(1)
    
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
    
    # kubeconfig server를 EC2 퍼블릭 IP로 변경 (k3s 기본은 127.0.0.1 → CI 러너에서 접근 불가)
    _rewrite_kubeconfig_server(kubeconfig_path, ec2_ip)
    
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

