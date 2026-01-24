#!/usr/bin/env python3
"""
Kubernetes에 애플리케이션을 배포하는 스크립트
"""

import os
import re
import subprocess
import sys
import json
import boto3
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

def run_kubectl_with_output(cmd, check=True):
    """kubectl 명령어 실행 (성공/실패 여부와 출력 반환)"""
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
        return True, result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stdout.strip() if hasattr(e, 'stdout') else '', e.stderr.strip() if hasattr(e, 'stderr') else str(e)

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
    success, stdout, stderr = run_kubectl_with_output(f"get namespace {namespace}", check=False)
    if not success or "NotFound" in stderr:
        # 네임스페이스가 없으면 생성
        print_info(f"Creating namespace '{namespace}'...")
        # YAML로 생성 (더 안정적)
        namespace_yaml = f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(namespace_yaml)
            temp_file = f.name
        
        try:
            success, stdout, stderr = run_kubectl_with_output(f"apply -f {temp_file}")
            if not success:
                print_error(f"Failed to create namespace: {stderr}")
                sys.exit(1)
            print_success(f"Namespace '{namespace}' created")
        finally:
            try:
                os.remove(temp_file)
            except:
                pass
    else:
        print_info(f"Namespace '{namespace}' already exists")

def create_ecr_secret(namespace, aws_region, ecr_repository_url):
    """ECR 인증을 위한 imagePullSecret 생성"""
    print_info("Creating ECR imagePullSecret...")
    
    # ECR 로그인 토큰 가져오기
    try:
        import boto3
        ecr_client = boto3.client('ecr', region_name=aws_region)
        token_response = ecr_client.get_authorization_token()
        token = token_response['authorizationData'][0]['authorizationToken']
        
        # Base64 디코딩하여 username:password 분리
        import base64
        decoded = base64.b64decode(token).decode('utf-8')
        username, password = decoded.split(':')
        
        # ECR 레지스트리 URL 추출
        registry = ecr_repository_url.split('/')[0]
        
        # Docker config JSON 생성
        docker_config = {
            "auths": {
                registry: {
                    "username": username,
                    "password": password,
                    "auth": token
                }
            }
        }
        
        import json
        docker_config_json = json.dumps(docker_config)
        
        # Kubernetes Secret 생성
        secret_name = "ecr-registry-secret"
        run_kubectl(
            f"delete secret {secret_name} -n {namespace} --ignore-not-found=true",
            check=False
        )
        
        # base64 인코딩
        import base64
        docker_config_b64 = base64.b64encode(docker_config_json.encode('utf-8')).decode('utf-8')
        
        # Secret YAML 생성
        secret_yaml = f"""apiVersion: v1
kind: Secret
metadata:
  name: {secret_name}
  namespace: {namespace}
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: {docker_config_b64}
"""
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(secret_yaml)
            temp_file = f.name
        
        try:
            success, stdout, stderr = run_kubectl_with_output(f"apply -f {temp_file}")
            if not success:
                print_error(f"Failed to create ECR secret: {stderr}")
                return False
            print_success("ECR imagePullSecret created successfully")
            return True
        finally:
            try:
                os.remove(temp_file)
            except:
                pass
    except Exception as e:
        print_error(f"Failed to create ECR secret: {e}")
        return False

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
    
    if not os.path.exists(abs_file_path):
        print_error(f"Manifest file not found: {abs_file_path}")
        sys.exit(1)
    
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
            
            print_info(f"Applying manifest: {os.path.basename(file_path)}")
            success, stdout, stderr = run_kubectl_with_output(f"apply -f {temp_file}")
            if not success:
                print_error(f"Failed to apply manifest: {os.path.basename(file_path)}")
                if stderr:
                    print_error(f"Error: {stderr}")
                sys.exit(1)
            print_success(f"Manifest applied: {os.path.basename(file_path)}")
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
        print_info(f"Applying manifest: {os.path.basename(file_path)}")
        success, stdout, stderr = run_kubectl_with_output(f"apply -f {abs_file_path}")
        if not success:
            print_error(f"Failed to apply manifest: {os.path.basename(file_path)}")
            if stderr:
                print_error(f"Error: {stderr}")
            sys.exit(1)
        print_success(f"Manifest applied: {os.path.basename(file_path)}")

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

def get_terraform_outputs(terraform_dir: str = 'terraform') -> dict:
    """Terraform output 값 가져오기"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    terraform_path = project_root / terraform_dir
    
    if not terraform_path.exists():
        print_info(f"Terraform directory not found: {terraform_path}")
        return {}
    
    try:
        result = subprocess.run(
            ['terraform', 'output', '-json'],
            capture_output=True,
            text=True,
            cwd=str(terraform_path),
            check=True
        )
        
        outputs = json.loads(result.stdout)
        return {k: v.get('value', '') for k, v in outputs.items()}
    except Exception as e:
        print_info(f"Failed to get Terraform outputs: {e}")
        return {}

def get_jwt_secret_from_secrets_manager(secret_arn: str, region: str = 'ap-northeast-2') -> str:
    """Secrets Manager에서 JWT Secret 가져오기"""
    try:
        client = boto3.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_arn)
        secret_string = response['SecretString']
        
        # JSON 형식인지 확인
        try:
            secret_data = json.loads(secret_string)
            # JSON 객체인 경우 JWT_SECRET 키로 찾기
            if isinstance(secret_data, dict):
                if 'JWT_SECRET' in secret_data:
                    return secret_data['JWT_SECRET']
                elif 'jwt_secret' in secret_data:
                    return secret_data['jwt_secret']
                else:
                    # 첫 번째 값 반환 (키가 다른 경우)
                    return list(secret_data.values())[0] if secret_data else None
        except json.JSONDecodeError:
            # JSON이 아닌 경우 단순 문자열로 저장된 것으로 간주
            pass
        
        # 단순 문자열로 저장된 경우 그대로 반환
        return secret_string
    except Exception as e:
        print_info(f"Failed to get JWT secret from Secrets Manager: {e}")
        return None

def setup_kubeconfig_for_local(terraform_outputs: dict):
    """로컬에서 실행 시 kubeconfig의 server 주소를 Public IP로 설정"""
    public_ip = terraform_outputs.get('ec2_public_ip', '')
    if not public_ip:
        print_info("EC2 Public IP not found, skipping kubeconfig update")
        return
    
    kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
    if not os.path.exists(kubeconfig_path):
        print_info(f"kubeconfig not found at {kubeconfig_path}")
        print_info("Please run 'python scripts/setup_local_kubeconfig.py' first")
        return
    
    try:
        # kubeconfig 읽기
        with open(kubeconfig_path, 'r') as f:
            content = f.read()
        
        # server 주소 추출
        import re
        server_match = re.search(r'server:\s+https://([^:]+):6443', content)
        if not server_match:
            print_info("Could not find server address in kubeconfig")
            return
        
        current_server_ip = server_match.group(1)
        
        # 이미 올바른 IP로 설정되어 있으면 변경하지 않음
        if current_server_ip == public_ip:
            print_info(f"kubeconfig already configured with Public IP: {public_ip}")
            return
        
        # Private IP (10.x.x.x, 172.x.x.x, 127.0.0.1)인 경우에만 자동 변경
        # Public IP로 이미 설정되어 있으면 사용자가 수동으로 설정한 것으로 간주하고 변경하지 않음
        is_private_ip = (
            current_server_ip.startswith('10.') or 
            current_server_ip.startswith('172.') or
            current_server_ip == '127.0.0.1' or
            current_server_ip.startswith('192.168.')
        )
        
        if not is_private_ip:
            print_info(f"kubeconfig server is set to {current_server_ip} (not a private IP)")
            print_info("Skipping automatic update to preserve manual configuration.")
            return
        
        # Private IP인 경우에만 Public IP로 변경
        pattern = r'server:\s+https://[^:]+:6443'
        new_server = f'server: https://{public_ip}:6443'
        
        if re.search(pattern, content):
            # 백업 생성
            backup_path = f"{kubeconfig_path}.backup"
            with open(backup_path, 'w') as f:
                f.write(content)
            
            content = re.sub(pattern, new_server, content)
            with open(kubeconfig_path, 'w') as f:
                f.write(content)
            print_success(f"kubeconfig updated: server -> https://{public_ip}:6443")
            print_info(f"Backup saved to: {backup_path}")
    except Exception as e:
        print_info(f"Failed to update kubeconfig: {e}")

def main():
    """메인 함수"""
    print("🚀 Deploying to Kubernetes...")
    
    # Terraform outputs 가져오기
    print_info("Getting Terraform outputs...")
    terraform_outputs = get_terraform_outputs()
    
    # 로컬에서 실행 시 kubeconfig 자동 설정
    setup_kubeconfig_for_local(terraform_outputs)
    
    # 환경 변수 설정 (Terraform output 우선, 없으면 환경 변수, 마지막으로 기본값)
    kubeconfig = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
    namespace = os.getenv('NAMESPACE', 'authcore')
    environment = os.getenv('ENVIRONMENT', 'prod')
    aws_region = os.getenv('AWS_REGION', terraform_outputs.get('aws_region', 'ap-northeast-2'))
    
    # DynamoDB 테이블 이름 (Terraform output에서 가져오기)
    users_table = os.getenv('USERS_TABLE', terraform_outputs.get('users_table_name', 'AuthCore_Users'))
    tokens_table = os.getenv('REFRESH_TOKENS_TABLE', terraform_outputs.get('refresh_tokens_table_name', 'AuthCore_RefreshTokens'))
    
    # JWT Secret 가져오기 (Secrets Manager 우선)
    jwt_secret = os.getenv('JWT_SECRET')
    if not jwt_secret:
        # Secrets Manager에서 가져오기 시도
        secrets_arn = terraform_outputs.get('secrets_manager_arn', '')
        if secrets_arn:
            print_info("Getting JWT secret from Secrets Manager...")
            jwt_secret = get_jwt_secret_from_secrets_manager(secrets_arn, aws_region)
        
        # 여전히 없으면 기본값
        if not jwt_secret:
            jwt_secret = 'your-super-secret-jwt-key-change-this-in-production'
            print_info("⚠️  Using default JWT secret. Set JWT_SECRET environment variable or use Secrets Manager.")
    
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
    
    # ECR imagePullSecret 생성
    ecr_repo_url = terraform_outputs.get('ecr_repository_url', '')
    if ecr_repo_url:
        create_ecr_secret(namespace, aws_region, ecr_repo_url)
    
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
    if not deployment_file.exists():
        print_error(f"Deployment file not found: {deployment_file}")
        sys.exit(1)
    
    print_info("Deploying application...")
    apply_manifest(str(deployment_file), {'IMAGE_URI': image_uri})
    
    # Service 배포
    service_file = project_root / 'k8s' / 'service.yaml'
    if not service_file.exists():
        print_error(f"Service file not found: {service_file}")
        sys.exit(1)
    
    print_info("Deploying service...")
    apply_manifest(str(service_file))
    
    # 리소스 생성 확인
    print_info("Verifying resources...")
    success, stdout, stderr = run_kubectl_with_output(f"get all -n {namespace}")
    if not success:
        print_error(f"Failed to verify resources: {stderr}")
    else:
        print_info("Resources in namespace:")
        print(stdout)
    
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
    
    # API Gateway 백엔드 업데이트 (선택사항)
    update_apigateway = os.getenv('UPDATE_API_GATEWAY', 'false').lower() == 'true'
    if update_apigateway:
        print_info("\n📋 Updating API Gateway backend...")
        script_dir = Path(__file__).parent
        update_script = script_dir / 'update_apigateway_backend.py'
        if update_script.exists():
            try:
                subprocess.run(
                    ['python3', str(update_script)],
                    check=False,
                    cwd=script_dir.parent
                )
            except Exception as e:
                print_error(f"Failed to update API Gateway: {e}")
        else:
            print_info("API Gateway update script not found, skipping...")
    else:
        print_info("\n💡 To update API Gateway backend, run:")
        print_info("   python scripts/update_apigateway_backend.py")
    
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

