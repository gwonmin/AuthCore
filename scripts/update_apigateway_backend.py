#!/usr/bin/env python3
"""
Kubernetes LoadBalancer URL을 가져와서 API Gateway Integration을 업데이트하는 스크립트
"""

import os
import sys
import boto3
import subprocess
import json
import time
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

def get_terraform_outputs(terraform_dir: str = 'terraform') -> dict:
    """Terraform output 값 가져오기"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    terraform_path = project_root / terraform_dir
    
    if not terraform_path.exists():
        print_error(f"Terraform directory not found: {terraform_path}")
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
        print_error(f"Failed to get Terraform outputs: {e}")
        return {}

def get_k8s_backend_url(namespace: str = 'authcore', service_name: str = 'authcore-api', timeout: int = 300) -> str:
    """Kubernetes 백엔드 URL 가져오기 (LoadBalancer 또는 NodePort)"""
    print_step(f"Getting backend URL from Kubernetes...")
    
    kubeconfig = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
    
    # 1. LoadBalancer 확인 (k3s는 klipper-lb 사용, IP 또는 hostname 반환 가능)
    start_time = time.time()
    while True:
        try:
            # 먼저 hostname 확인
            hostname_cmd = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.status.loadBalancer.ingress[0].hostname}}'"
            hostname_result = subprocess.run(
                hostname_cmd,
                shell=True,
                capture_output=True,
                text=True,
                env={'KUBECONFIG': kubeconfig, **os.environ}
            )
            
            # IP 확인 (k3s는 IP를 반환할 수 있음)
            ip_cmd = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'"
            ip_result = subprocess.run(
                ip_cmd,
                shell=True,
                capture_output=True,
                text=True,
                env={'KUBECONFIG': kubeconfig, **os.environ}
            )
            
            # hostname 또는 IP 중 하나라도 있으면 사용
            hostname = hostname_result.stdout.strip() if hostname_result.returncode == 0 else ''
            ip = ip_result.stdout.strip() if ip_result.returncode == 0 else ''
            
            # 유효한 값이 있는지 확인
            url = None
            if hostname and hostname not in ['None', '<pending>', '']:
                url = hostname
            elif ip and ip not in ['None', '<pending>', '']:
                url = ip
            
            if url:
                # HTTP 프로토콜 추가
                if not url.startswith('http'):
                    url = f"http://{url}"
                print_success(f"LoadBalancer URL: {url}")
                return url
            
            elapsed = int(time.time() - start_time)
            if elapsed > 15:  # k3s는 빠르게 동작하므로 15초 후 NodePort로 전환
                break
            
            print_info(f"Waiting for LoadBalancer... (elapsed: {elapsed}s)")
            time.sleep(3)
        except Exception as e:
            print_info(f"LoadBalancer not available, trying NodePort: {e}")
            break
    
    # 2. LoadBalancer가 없거나 pending이면 NodePort 사용 (k3s의 경우)
    print_info("LoadBalancer not available or pending, using NodePort or LoadBalancer port...")
    
    # Service 타입 확인
    service_type_cmd = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.spec.type}}'"
    result = subprocess.run(
        service_type_cmd,
        shell=True,
        capture_output=True,
        text=True,
        env={'KUBECONFIG': kubeconfig, **os.environ}
    )
    service_type = result.stdout.strip()
    
    # NodePort 가져오기 (LoadBalancer도 NodePort를 사용함)
    nodeport_cmd = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.spec.ports[0].nodePort}}'"
    result = subprocess.run(
        nodeport_cmd,
        shell=True,
        capture_output=True,
        text=True,
        env={'KUBECONFIG': kubeconfig, **os.environ}
    )
    nodeport = result.stdout.strip()
    
    # NodePort가 없으면 LoadBalancer의 port 확인 (k3s는 port 80을 사용할 수 있음)
    if not nodeport or nodeport == 'None':
        # LoadBalancer의 port 확인
        port_cmd = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.spec.ports[0].port}}'"
        port_result = subprocess.run(
            port_cmd,
            shell=True,
            capture_output=True,
            text=True,
            env={'KUBECONFIG': kubeconfig, **os.environ}
        )
        port = port_result.stdout.strip()
        if port and port != 'None':
            nodeport = port  # LoadBalancer의 port 사용
    
    if nodeport and nodeport != 'None':
        # EC2 Public IP 가져오기 (Terraform output에서)
        ec2_ip = os.getenv('EC2_PUBLIC_IP', '')
        if not ec2_ip:
            # Terraform output에서 가져오기 시도
            terraform_outputs = get_terraform_outputs()
            ec2_ip = terraform_outputs.get('ec2_public_ip', '')
        
        if ec2_ip:
            url = f"http://{ec2_ip}:{nodeport}"
            print_success(f"Backend URL (EC2 IP:Port): {url}")
            print_info(f"  EC2 IP: {ec2_ip}")
            print_info(f"  NodePort: {nodeport}")
            return url
        else:
            print_error("EC2 Public IP not found. Set EC2_PUBLIC_IP environment variable.")
            return ""
    else:
        print_error("NodePort or port not found")
        return ""

def update_api_gateway_integration(api_id: str, integration_id: str, backend_url: str, region: str = 'ap-northeast-2'):
    """API Gateway Integration 업데이트 (변경된 경우에만)"""
    print_step(f"Checking API Gateway Integration...")
    
    client = boto3.client('apigatewayv2', region_name=region)
    
    try:
        # 기존 Integration 정보 가져오기
        integration = client.get_integration(
            ApiId=api_id,
            IntegrationId=integration_id
        )
        
        current_uri = integration.get('IntegrationUri', '')
        
        # 백엔드 URL이 동일한지 확인
        if current_uri == backend_url:
            print_info(f"Backend URL unchanged, skipping update")
            print_info(f"  Current URL: {current_uri}")
            print_info(f"  New URL: {backend_url}")
            return True
        
        # 백엔드 URL이 변경된 경우에만 업데이트
        print_info(f"Backend URL changed, updating Integration...")
        print_info(f"  Current URL: {current_uri}")
        print_info(f"  New URL: {backend_url}")
        
        response = client.update_integration(
            ApiId=api_id,
            IntegrationId=integration_id,
            IntegrationUri=backend_url,
            IntegrationMethod='ANY',
            PayloadFormatVersion='1.0',
            ConnectionType='INTERNET',
            RequestParameters={
                'overwrite:path': '$request.path'
            }
        )
        
        print_success(f"API Gateway Integration updated successfully")
        print_info(f"  Integration ID: {integration_id}")
        print_info(f"  Backend URL: {backend_url}")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to update API Gateway Integration: {e}")
        return False

def get_api_gateway_integration(api_id: str, region: str = 'ap-northeast-2'):
    """API Gateway Integration ID 가져오기"""
    client = boto3.client('apigatewayv2', region_name=region)
    
    try:
        integrations = client.get_integrations(ApiId=api_id)
        
        # k8s_backend Integration 찾기
        for integration in integrations.get('Items', []):
            if integration.get('IntegrationType') == 'HTTP_PROXY':
                return integration.get('IntegrationId')
        
        return None
        
    except Exception as e:
        print_error(f"Failed to get API Gateway Integrations: {e}")
        return None

def create_api_gateway_integration(api_id: str, backend_url: str, region: str = 'ap-northeast-2'):
    """API Gateway Integration 생성"""
    client = boto3.client('apigatewayv2', region_name=region)
    
    try:
        response = client.create_integration(
            ApiId=api_id,
            IntegrationType='HTTP_PROXY',
            IntegrationUri=backend_url,
            IntegrationMethod='ANY',
            PayloadFormatVersion='1.0',
            ConnectionType='INTERNET',
            RequestParameters={
                'overwrite:path': '$request.path'
            }
        )
        
        integration_id = response.get('IntegrationId')
        print_success(f"API Gateway Integration created: {integration_id}")
        return integration_id
        
    except Exception as e:
        print_error(f"Failed to create API Gateway Integration: {e}")
        return None

def create_api_gateway_routes(api_id: str, integration_id: str, region: str = 'ap-northeast-2'):
    """API Gateway Routes 생성"""
    client = boto3.client('apigatewayv2', region_name=region)
    
    routes_to_create = [
        {'route_key': '$default', 'description': 'Default route - all paths'},
        {'route_key': 'ANY /auth/{proxy+}', 'description': 'Auth routes'},
        {'route_key': 'GET /health', 'description': 'Health check'}
    ]
    
    created_routes = []
    
    for route_config in routes_to_create:
        try:
            # 기존 라우트 확인
            routes = client.get_routes(ApiId=api_id)
            existing_route = None
            for route in routes.get('Items', []):
                if route.get('RouteKey') == route_config['route_key']:
                    existing_route = route
                    break
            
            if existing_route:
                print_info(f"Route already exists: {route_config['route_key']}")
                created_routes.append(existing_route.get('RouteId'))
            else:
                response = client.create_route(
                    ApiId=api_id,
                    RouteKey=route_config['route_key'],
                    Target=f"integrations/{integration_id}"
                )
                route_id = response.get('RouteId')
                print_success(f"Route created: {route_config['route_key']} ({route_id})")
                created_routes.append(route_id)
                
        except Exception as e:
            print_error(f"Failed to create route {route_config['route_key']}: {e}")
    
    return created_routes

def main():
    """메인 함수"""
    print("=" * 60)
    print("🔗 API Gateway Backend Update Script")
    print("=" * 60)
    
    # 환경 변수 설정
    aws_region = os.getenv('AWS_REGION', 'ap-northeast-2')
    namespace = os.getenv('NAMESPACE', 'authcore')
    service_name = os.getenv('SERVICE_NAME', 'authcore-api')
    
    # 1. Terraform outputs 가져오기
    print_step("Step 1: Getting Terraform outputs...")
    outputs = get_terraform_outputs()
    
    api_gateway_id = outputs.get('api_gateway_id', '')
    if not api_gateway_id:
        # 환경 변수에서 가져오기 시도
        api_gateway_id = os.getenv('API_GATEWAY_ID', '')
    
    if not api_gateway_id:
        print_error("API Gateway ID not found")
        print_info("Set API_GATEWAY_ID environment variable or ensure terraform/apigateway.tf is applied")
        sys.exit(1)
    
    print_success(f"API Gateway ID: {api_gateway_id}")
    
    # 2. Kubernetes 백엔드 URL 가져오기 (LoadBalancer 또는 NodePort)
    print_step("Step 2: Getting Kubernetes backend URL...")
    loadbalancer_url = get_k8s_backend_url(namespace, service_name)
    
    if not loadbalancer_url:
        print_error("Failed to get LoadBalancer URL")
        print_info("Make sure Kubernetes service is deployed and LoadBalancer is ready")
        sys.exit(1)
    
    # 3. API Gateway Integration 가져오기 또는 생성
    print_step("Step 3: Getting or creating API Gateway Integration...")
    integration_id = get_api_gateway_integration(api_gateway_id, aws_region)
    
    if not integration_id:
        print_info("Integration not found, creating new one...")
        integration_id = create_api_gateway_integration(api_gateway_id, loadbalancer_url, aws_region)
        if not integration_id:
            print_error("Failed to create API Gateway Integration")
            sys.exit(1)
    else:
        print_success(f"Integration ID: {integration_id}")
        # 4. API Gateway Integration 업데이트 (변경된 경우에만)
        print_step("Step 4: Checking and updating API Gateway Integration if needed...")
        if not update_api_gateway_integration(api_gateway_id, integration_id, loadbalancer_url, aws_region):
            print_error("Failed to update API Gateway Integration")
            sys.exit(1)
    
    # 5. API Gateway Routes 생성
    print_step("Step 5: Creating API Gateway Routes...")
    create_api_gateway_routes(api_gateway_id, integration_id, aws_region)
    
    print_success("API Gateway backend configured successfully!")
    print_info(f"API Gateway URL: {outputs.get('api_gateway_url', '')}")
    print_info(f"Backend URL: {loadbalancer_url}")
    
    print("\n" + "=" * 60)
    print("✅ API Gateway Backend Update Completed!")
    print("=" * 60)

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
