#!/usr/bin/env python3
"""
기존 API Gateway를 찾는 스크립트
"""

import os
import sys
import boto3
import json

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

def list_api_gateways_v2(region: str = 'ap-northeast-2'):
    """API Gateway V2 (HTTP API) 목록 조회"""
    client = boto3.client('apigatewayv2', region_name=region)
    
    try:
        response = client.get_apis()
        return response.get('Items', [])
    except Exception as e:
        print_error(f"Failed to list API Gateways: {e}")
        return []

def list_api_gateways_v1(region: str = 'ap-northeast-2'):
    """API Gateway V1 (REST API) 목록 조회"""
    client = boto3.client('apigateway', region_name=region)
    
    try:
        response = client.get_rest_apis()
        return response.get('items', [])
    except Exception as e:
        print_error(f"Failed to list REST APIs: {e}")
        return []

def find_api_gateway_by_name(name_pattern: str, region: str = 'ap-northeast-2'):
    """이름 패턴으로 API Gateway 찾기"""
    print_step(f"Searching for API Gateway with pattern: '{name_pattern}'...")
    
    # V2 (HTTP API) 검색
    v2_apis = list_api_gateways_v2(region)
    matches = []
    
    for api in v2_apis:
        api_name = api.get('Name', '')
        api_id = api.get('ApiId', '')
        api_endpoint = api.get('ApiEndpoint', '')
        
        if name_pattern.lower() in api_name.lower():
            matches.append({
                'type': 'HTTP API (V2)',
                'id': api_id,
                'name': api_name,
                'endpoint': api_endpoint,
                'protocol': api.get('ProtocolType', 'HTTP')
            })
    
    # V1 (REST API) 검색
    v1_apis = list_api_gateways_v1(region)
    for api in v1_apis:
        api_name = api.get('name', '')
        api_id = api.get('id', '')
        
        if name_pattern.lower() in api_name.lower():
            matches.append({
                'type': 'REST API (V1)',
                'id': api_id,
                'name': api_name,
                'endpoint': f"https://{api_id}.execute-api.{region}.amazonaws.com",
                'protocol': 'REST'
            })
    
    return matches

def main():
    """메인 함수"""
    print("=" * 60)
    print("🔍 API Gateway 찾기")
    print("=" * 60)
    
    aws_region = os.getenv('AWS_REGION', 'ap-northeast-2')
    search_pattern = sys.argv[1] if len(sys.argv) > 1 else 'authcore'
    
    print_info(f"Region: {aws_region}")
    print_info(f"Search pattern: '{search_pattern}'")
    print()
    
    # 1. 모든 API Gateway V2 목록
    print_step("Step 1: Listing all HTTP APIs (V2)...")
    v2_apis = list_api_gateways_v2(aws_region)
    
    if v2_apis:
        print_success(f"Found {len(v2_apis)} HTTP API(s):")
        print()
        for api in v2_apis:
            print(f"  📌 Name: {api.get('Name', 'N/A')}")
            print(f"     ID: {api.get('ApiId', 'N/A')}")
            print(f"     Endpoint: {api.get('ApiEndpoint', 'N/A')}")
            print(f"     Protocol: {api.get('ProtocolType', 'N/A')}")
            print()
    else:
        print_info("No HTTP APIs found")
        print()
    
    # 2. 모든 REST API 목록
    print_step("Step 2: Listing all REST APIs (V1)...")
    v1_apis = list_api_gateways_v1(aws_region)
    
    if v1_apis:
        print_success(f"Found {len(v1_apis)} REST API(s):")
        print()
        for api in v1_apis:
            print(f"  📌 Name: {api.get('name', 'N/A')}")
            print(f"     ID: {api.get('id', 'N/A')}")
            print(f"     Endpoint: https://{api.get('id', 'N/A')}.execute-api.{aws_region}.amazonaws.com")
            print()
    else:
        print_info("No REST APIs found")
        print()
    
    # 3. 패턴으로 검색
    print_step(f"Step 3: Searching for APIs matching '{search_pattern}'...")
    matches = find_api_gateway_by_name(search_pattern, aws_region)
    
    if matches:
        print_success(f"Found {len(matches)} matching API Gateway(s):")
        print()
        for i, match in enumerate(matches, 1):
            print(f"  {i}. {match['type']}")
            print(f"     Name: {match['name']}")
            print(f"     ID: {match['id']}")
            print(f"     Endpoint: {match['endpoint']}")
            print()
        
        # Terraform 변수 형식으로 출력
        print("=" * 60)
        print("💡 Terraform에서 사용하려면:")
        print("=" * 60)
        if len(matches) == 1:
            match = matches[0]
            print(f"\n# terraform.tfvars 또는 terraform/variables.tf에 추가:")
            print(f'existing_api_gateway_name = "{match["id"]}"')
            print(f"\n# 또는 환경 변수로:")
            print(f'export TF_VAR_existing_api_gateway_name="{match["id"]}"')
        else:
            print("\n여러 개가 발견되었습니다. 원하는 API Gateway의 ID를 선택하세요:")
            for i, match in enumerate(matches, 1):
                print(f'\n# 옵션 {i}: {match["name"]}')
                print(f'existing_api_gateway_name = "{match["id"]}"')
    else:
        print_info(f"No API Gateway found matching '{search_pattern}'")
        print("\n💡 모든 API Gateway를 보려면:")
        print("   python scripts/find_api_gateway.py")
    
    print("\n" + "=" * 60)
    print("✅ 완료!")
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
