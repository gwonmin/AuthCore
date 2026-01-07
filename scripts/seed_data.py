#!/usr/bin/env python3
"""
DynamoDB 테이블에 초기 데이터(Seed Data)를 삽입하는 스크립트
Terraform으로 테이블 생성 후 실행
"""

import boto3
import bcrypt
import json
import os
import sys
from datetime import datetime
from typing import List, Dict

# AWS 리전 설정
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')

# DynamoDB 클라이언트 생성
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)


def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def seed_users(table_name: str, users_data: List[Dict]) -> None:
    """Users 테이블에 초기 사용자 데이터 삽입"""
    table = dynamodb.Table(table_name)
    
    print(f"\n📦 Seeding users to {table_name}...")
    
    for user in users_data:
        try:
            # 비밀번호 해싱
            if 'password' in user:
                user['password_hash'] = hash_password(user['password'])
                del user['password']  # 원본 비밀번호 제거
            
            # 타임스탬프 추가
            if 'created_at' not in user:
                user['created_at'] = datetime.utcnow().isoformat()
            
            # 기본값 설정
            if 'is_active' not in user:
                user['is_active'] = True
            
            # DynamoDB에 삽입
            table.put_item(Item=user)
            print(f"  ✅ Seeded user: {user.get('username', user.get('user_id'))}")
            
        except Exception as e:
            print(f"  ❌ Failed to seed user {user.get('username', 'unknown')}: {e}")


def load_seed_data(file_path: str) -> Dict:
    """JSON 파일에서 seed 데이터 로드"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Seed data file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {file_path}: {e}")
        return {}


def main():
    """메인 함수"""
    print("🚀 Starting DynamoDB seed data insertion...")
    
    # Terraform output에서 테이블명 가져오기 (환경 변수 또는 직접 지정)
    users_table = os.getenv('USERS_TABLE_NAME', 'AuthCore_Users')
    tokens_table = os.getenv('REFRESH_TOKENS_TABLE_NAME', 'AuthCore_RefreshTokens')
    
    # Seed 데이터 파일 경로
    seed_data_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data',
        'seed_users.json'
    )
    
    # Seed 데이터 로드
    seed_data = load_seed_data(seed_data_file)
    
    if not seed_data:
        print("⚠️  No seed data found. Using default test users...")
        # 기본 테스트 사용자
        default_users = [
            {
                'user_id': 'admin-001',
                'username': 'admin',
                'password': 'admin123',
                'is_active': True
            },
            {
                'user_id': 'test-001',
                'username': 'testuser',
                'password': 'testpass123',
                'is_active': True
            }
        ]
        seed_users(users_table, default_users)
    else:
        # JSON 파일에서 사용자 데이터 가져오기
        users = seed_data.get('users', [])
        if users:
            seed_users(users_table, users)
        else:
            print("⚠️  No users found in seed data file")
    
    print("\n✅ Seed data insertion completed!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

