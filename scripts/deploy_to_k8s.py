#!/usr/bin/env python3
"""
Kubernetes에 애플리케이션을 배포하는 스크립트
"""

import os
import re
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

def run_kubectl(cmd, check=True):
    """kubectl 명령어 실행"""
    kubeconfig = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
    env = os.environ.copy()
    env['KUBECONFIG'] = kubeconfig
    
    try:
        result = subprocess.run(
            f"kubectl {cmd}",
            shell=True,
            check=check,
            capture_output=True,
            text=True,
            env=env
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print_error(f"kubectl command failed: {cmd}")
        if e.stderr:
            print_error(e.stderr)
        return None

def check_kubectl():
    """kubectl 설치 확인"""
    try:
        subprocess.run("kubectl version --client", shell=True, check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_cluster_connection():
    """클러스터 연결 확인"""
    result = run_kubectl("cluster-info", check=False)
    return result is not None

def create_namespace(namespace):
    """네임스페이스 생성"""
    print_info("Creating namespace...")
    # 네임스페이스가 이미 존재하는지 확인
    result = run_kubectl(f"get namespace {namespace}", check=False)
    if result is None:
        # 네임스페이스가 없으면 생성
        run_kubectl(f"create namespace {namespace}")
    else:
        print_info(f"Namespace '{namespace}' already exists")

def create_secrets(namespace, jwt_secret):
    """Secret 생성"""
    print_info("Creating secrets...")
    # 기존 Secret 삭제 후 재생성 (업데이트를 위해)
    run_kubectl(f"delete secret authcore-secrets -n {namespace} --ignore-not-found=true", check=False)
    
    # JWT_SECRET에 특수문자가 있을 수 있으므로 이스케이프 처리
    escaped_secret = str(jwt_secret).replace('"', '\\"').replace("'", "\\'").replace('$', '\\$')
    result = run_kubectl(
        f"create secret generic authcore-secrets "
        f"--from-literal=JWT_SECRET=\"{escaped_secret}\" "
        f"--namespace={namespace}",
        check=False
    )
    if result is None:
        print_error("Failed to create secret")
        sys.exit(1)
    print_success("Secret created successfully")

def create_configmap(namespace, config):
    """ConfigMap 생성"""
    print_info("Creating ConfigMap...")
    # 기존 ConfigMap 삭제 후 재생성 (업데이트를 위해)
    run_kubectl(f"delete configmap authcore-config -n {namespace} --ignore-not-found=true", check=False)
    
    cmd = f"create configmap authcore-config --namespace={namespace}"
    for key, value in config.items():
        # 값에 특수문자가 있을 수 있으므로 이스케이프 처리
        escaped_value = str(value).replace('"', '\\"').replace("'", "\\'").replace('$', '\\$')
        cmd += f" --from-literal={key}=\"{escaped_value}\""
    result = run_kubectl(cmd, check=False)
    if result is None:
        print_error("Failed to create ConfigMap")
        sys.exit(1)
    print_success("ConfigMap created successfully")

def load_image_uri():
    """이미지 URI 로드"""
    # 프로젝트 루트 디렉토리 찾기
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    image_uri_file = project_root / '.image_uri'
    
    if image_uri_file.exists():
        try:
            with open(image_uri_file, 'r', encoding='utf-8') as f:
                line = f.read().strip()
                # export IMAGE_URI=... 형식에서 URI 추출
                if '=' in line:
                    uri = line.split('=', 1)[1].strip()
                    # 따옴표 제거
                    if uri.startswith('"') and uri.endswith('"'):
                        uri = uri[1:-1]
                    elif uri.startswith("'") and uri.endswith("'"):
                        uri = uri[1:-1]
                    return uri
        except Exception as e:
            print_error(f"Failed to read image URI file: {e}")
    return os.getenv('IMAGE_URI')

def apply_manifest(file_path, env_vars=None):
    """매니페스트 파일 적용"""
    # 절대 경로로 변환
    abs_file_path = os.path.abspath(file_path)
    
    if env_vars:
        # 환경 변수 치환 (${KEY} 형식 지원)
        with open(abs_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for key, value in env_vars.items():
                # ${KEY} 형식만 치환 (더 정확한 매칭)
                # 먼저 ${KEY} 형식 치환
                placeholder = f"${{{key}}}"
                if placeholder in content:
                    content = content.replace(placeholder, str(value))
                else:
                    # $KEY 형식도 시도 (하위 호환성, 하지만 주의: 다른 변수와 충돌 가능)
                    # 예: $IMAGE_URI는 $IMAGE_URI_OLD와 충돌할 수 있으므로 ${} 형식 권장
                    # 단어 경계 확인 (더 안전한 치환)
                    pattern = re.compile(r'\$' + re.escape(key) + r'(?![a-zA-Z0-9_])')
                    content = pattern.sub(str(value), content)
        
        # 임시 파일에 저장 후 적용
        temp_file = f"{abs_file_path}.tmp"
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            result = run_kubectl(f"apply -f {temp_file}", check=False)
            if result is None:
                print_error(f"Failed to apply manifest: {temp_file}")
                sys.exit(1)
        except Exception as e:
            print_error(f"Failed to apply manifest: {e}")
            raise
        finally:
            # 임시 파일 정리
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print_error(f"Failed to remove temp file: {e}")
    else:
        result = run_kubectl(f"apply -f {abs_file_path}", check=False)
        if result is None:
            print_error(f"Failed to apply manifest: {abs_file_path}")
            sys.exit(1)

def wait_for_deployment(namespace, deployment_name, timeout=300):
    """배포 완료 대기"""
    print_info(f"Waiting for deployment '{deployment_name}' to be ready...")
    result = run_kubectl(
        f"rollout status deployment/{deployment_name} "
        f"-n {namespace} --timeout={timeout}s",
        check=False
    )
    if result is None:
        print_error(f"Deployment {deployment_name} failed or timed out after {timeout}s")
        # Pod 상태 확인
        print_info("Checking pod status...")
        # deployment의 label selector 사용 (app=authcore-api)
        run_kubectl(f"get pods -n {namespace} -l app=authcore-api", check=False)
        # Pod 로그 확인
        print_info("Checking pod logs (last 20 lines)...")
        pods_result = run_kubectl(
            f"get pods -n {namespace} -l app=authcore-api -o jsonpath='{{.items[0].metadata.name}}'",
            check=False
        )
        if pods_result:
            run_kubectl(f"logs -n {namespace} {pods_result} --tail=20", check=False)
        sys.exit(1)
    print_success(f"Deployment '{deployment_name}' is ready")

def main():
    """메인 함수"""
    print("🚀 Deploying to Kubernetes...")
    
    # 환경 변수 설정
    kubeconfig = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
    namespace = os.getenv('NAMESPACE', 'authcore')
    environment = os.getenv('ENVIRONMENT', 'prod')
    aws_region = os.getenv('AWS_REGION', 'ap-northeast-2')
    jwt_secret = os.getenv('JWT_SECRET', 'your-super-secret-jwt-key-change-this-in-production')
    users_table = os.getenv('USERS_TABLE', 'AuthCore_Users')
    tokens_table = os.getenv('REFRESH_TOKENS_TABLE', 'AuthCore_RefreshTokens')
    
    # kubectl 확인
    if not check_kubectl():
        print_error("kubectl is not installed")
        sys.exit(1)
    
    # kubeconfig 확인
    if not os.path.exists(kubeconfig):
        print_error(f"kubeconfig not found at {kubeconfig}")
        print_info("Copy kubeconfig from EC2:")
        print("   scp ubuntu@<EC2_IP>:/home/ubuntu/.kube/config ~/.kube/config")
        print_info("Or run: python scripts/setup_k8s.py")
        sys.exit(1)
    
    # KUBECONFIG 환경 변수 설정
    os.environ['KUBECONFIG'] = kubeconfig
    
    # 클러스터 연결 확인
    print_info("Checking cluster connection...")
    if not check_cluster_connection():
        print_error("Cannot connect to Kubernetes cluster")
        sys.exit(1)
    
    print_success("Connected to cluster")
    run_kubectl("get nodes")
    
    # 네임스페이스 생성
    create_namespace(namespace)
    
    # Secret 생성
    create_secrets(namespace, jwt_secret)
    
    # ConfigMap 생성
    configmap_data = {
        'AWS_REGION': aws_region,
        'NODE_ENV': environment,
        'USERS_TABLE': users_table,
        'REFRESH_TOKENS_TABLE': tokens_table,
        'USERS_TABLE_NAME': users_table,  # 하위 호환성
        'REFRESH_TOKENS_TABLE_NAME': tokens_table  # 하위 호환성
    }
    create_configmap(namespace, configmap_data)
    
    # 이미지 URI 확인
    image_uri = load_image_uri()
    if not image_uri:
        print_error("Image URI not found")
        print_info("Set IMAGE_URI environment variable or run build_and_push.py first")
        sys.exit(1)
    
    print_info(f"Using image: {image_uri}")
    
    # 프로젝트 루트 디렉토리 찾기
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Deployment 배포
    deployment_file = project_root / 'k8s' / 'deployment.yaml'
    if deployment_file.exists():
        print_info("Deploying application...")
        apply_manifest(str(deployment_file), {'IMAGE_URI': image_uri})
    else:
        print_error(f"Deployment file not found: {deployment_file}")
        sys.exit(1)
    
    # Service 배포
    service_file = project_root / 'k8s' / 'service.yaml'
    if service_file.exists():
        print_info("Deploying service...")
        apply_manifest(str(service_file))
    else:
        print_error(f"Service file not found: {service_file}")
        sys.exit(1)
    
    # 배포 상태 확인
    wait_for_deployment(namespace, 'authcore-api')
    
    # 배포 정보 출력
    print_success("Deployment completed!")
    print_info("Deployment information:")
    run_kubectl(f"get pods -n {namespace}")
    run_kubectl(f"get svc -n {namespace}")
    
    # LoadBalancer URL 확인
    print_info("LoadBalancer URL:")
    result = run_kubectl(
        f"get svc authcore-api -n {namespace} "
        f"-o jsonpath='{{.status.loadBalancer.ingress[0].hostname}}'",
        check=False
    )
    if result:
        print(f"  {result}")
    else:
        print("  Pending...")
    
    print_success("Deployment successful!")

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

