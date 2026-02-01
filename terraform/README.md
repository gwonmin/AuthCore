# Terraform Infrastructure as Code

이 디렉토리는 AuthCore 프로젝트의 AWS 인프라를 Terraform으로 관리합니다.

## 📋 구조

- `main.tf` - Provider 설정
- `variables.tf` - 변수 정의
- `outputs.tf` - 출력값 정의
- `dynamodb.tf` - DynamoDB 테이블
- `ec2.tf` - EC2 인스턴스 (Kubernetes 노드)
- `vpc.tf` - VPC 및 서브넷
- `security-group.tf` - 보안 그룹
- `ecr.tf` - ECR 리포지토리
- `s3.tf` - S3 버킷
- `secrets.tf` - Secrets Manager
- `iam.tf` - IAM 역할 및 정책 (EC2 역할은 ec2.tf에 정의)

## 🚀 사용 방법

### 1. 초기화

**CI에서 plan/apply**를 쓰므로 state는 **S3 백엔드**를 사용합니다. bucket/key/region은 `init` 시 `-backend-config`로 전달합니다.

```bash
cd terraform
terraform init -reconfigure \
  -backend-config="bucket=YOUR_TERRAFORM_STATE_BUCKET" \
  -backend-config="key=authcore/prod/terraform.tfstate" \
  -backend-config="region=ap-northeast-2"
```

(로컬 state에서 S3로 이전 시: 위 `init -reconfigure` 실행 후 마이그레이션 프롬프트에서 `yes` 입력)

### 2. 계획 확인

```bash
terraform plan
```

### 3. 적용

```bash
terraform apply
```

### 4. 출력값 확인

```bash
terraform output
```

### 5. 인프라 제거

```bash
terraform destroy
```

## 🔧 변수 설정

`terraform.tfvars` 파일을 생성하여 변수를 설정할 수 있습니다:

```hcl
aws_region = "ap-northeast-2"
environment = "prod"
jwt_secret = "your-secret-key"
dynamodb_read_capacity = 5
dynamodb_write_capacity = 5
```

## 📝 출력값

Terraform 적용 후 다음 출력값을 사용할 수 있습니다:

- `users_table_name` - DynamoDB Users 테이블 이름
- `refresh_tokens_table_name` - DynamoDB RefreshTokens 테이블 이름
- `ec2_instance_id` - EC2 인스턴스 ID
- `ec2_public_ip` - EC2 인스턴스 Public IP
- `ec2_elastic_ip` - EC2 인스턴스 Elastic IP
- `ecr_repository_url` - ECR 리포지토리 URL
- `s3_bucket_name` - S3 버킷 이름
- `secrets_manager_arn` - Secrets Manager ARN
- `vpc_id` - VPC ID

## 🔗 Python 스크립트와 연동

Terraform 적용 후 `scripts/post_terraform_setup.py`를 실행하여:
1. Seed 데이터 삽입
2. S3 파일 업로드

을 자동으로 수행할 수 있습니다.

그 후 Kubernetes 배포:
1. Docker 이미지 빌드 및 푸시: `python scripts/build_and_push.py`
2. kubeconfig 설정: `python scripts/setup_k8s.py`
3. Kubernetes 배포: `python scripts/deploy_to_k8s.py`

