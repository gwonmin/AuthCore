# Python Scripts for IaC and Kubernetes

Terraform으로 인프라를 생성한 후 실행하는 Python 스크립트들입니다.

## 📋 스크립트 목록

### 1. `seed_data.py`
DynamoDB 테이블에 초기 데이터(Seed Data)를 삽입합니다.

**사용법:**
```bash
export USERS_TABLE_NAME="AuthCore_Users"
export REFRESH_TOKENS_TABLE_NAME="AuthCore_RefreshTokens"
python scripts/seed_data.py
```

### 2. `migrate_to_secrets.py`
환경 변수를 AWS Secrets Manager로 마이그레이션합니다.

**사용법:**
```bash
export SECRETS_MANAGER_NAME="authcore/config-prod"
python scripts/migrate_to_secrets.py
```

### 3. `build_and_push.py` 🆕
Podman을 사용하여 이미지를 빌드하고 ECR에 푸시합니다.

**사용법:**
```bash
export AWS_REGION="ap-northeast-2"
export ENVIRONMENT="prod"
export IMAGE_TAG="latest"
python scripts/build_and_push.py
```

**참고**: Podman이 설치되어 있어야 합니다. Docker와 호환되지만 rootless로 실행됩니다.

### 4. `deploy_to_k8s.py` 🆕
Kubernetes에 애플리케이션을 배포합니다.

**사용법:**
```bash
export KUBECONFIG="~/.kube/config"
export NAMESPACE="authcore"
export JWT_SECRET="your-secret-key"
export IMAGE_URI="123456789.dkr.ecr.ap-northeast-2.amazonaws.com/authcore-prod:latest"
python scripts/deploy_to_k8s.py
```

### 5. `setup_k8s.py` 🆕
EC2에서 kubeconfig를 복사하여 로컬 Kubernetes 접근을 설정합니다.

**사용법:**
```bash
export EC2_IP="1.2.3.4"
export SSH_KEY="~/.ssh/id_rsa"
python scripts/setup_k8s.py
```

## 🔧 사전 요구사항

### Python 패키지 설치
```bash
pip install -r requirements.txt
```

### AWS 자격 증명 설정
```bash
aws configure
```

또는 환경 변수 (⚠️ 절대 Git에 커밋하지 마세요):
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="ap-northeast-2"
```

### kubectl 설치 (Kubernetes 배포용)
```bash
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# macOS
brew install kubectl

# Windows
choco install kubernetes-cli
```

### Podman 설치 (이미지 빌드용)
```bash
# macOS
brew install podman
podman machine init
podman machine start

# Linux
# Ubuntu/Debian
sudo apt-get install -y podman

# Fedora/RHEL
sudo dnf install -y podman
```

## 🚀 전체 워크플로우

### Terraform 인프라 배포
```bash
# 1. Terraform으로 인프라 생성
cd terraform
terraform init
terraform plan
terraform apply

# 2. 출력값 확인
terraform output
```

### Kubernetes 클러스터 설정
```bash
# 1. EC2에 SSH 접속하여 Kubernetes 설치 확인
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP>
kubectl get nodes

# 2. 로컬에서 kubeconfig 복사
python scripts/setup_k8s.py
# 또는 수동으로:
# scp ubuntu@<EC2_IP>:~/.kube/config ~/.kube/config
```

### 애플리케이션 배포
```bash
# 1. Podman으로 이미지 빌드 및 ECR 푸시
python scripts/build_and_push.py

# 2. Kubernetes에 배포
python scripts/deploy_to_k8s.py
```

## 📝 환경 변수

각 스크립트는 다음 환경 변수를 사용합니다:

### 공통
- `AWS_REGION` - AWS 리전 (기본값: `ap-northeast-2`)

### DynamoDB 관련
- `USERS_TABLE_NAME` - DynamoDB Users 테이블 이름
- `REFRESH_TOKENS_TABLE_NAME` - DynamoDB RefreshTokens 테이블 이름

### Secrets Manager 관련
- `SECRETS_MANAGER_NAME` - Secrets Manager 시크릿 이름

### Kubernetes 관련
- `KUBECONFIG` - kubeconfig 파일 경로 (기본값: `~/.kube/config`)
- `NAMESPACE` - Kubernetes 네임스페이스 (기본값: `authcore`)
- `ENVIRONMENT` - 환경 이름 (기본값: `prod`)
- `JWT_SECRET` - JWT Secret Key
- `IMAGE_URI` - Docker 이미지 URI
- `EC2_IP` - EC2 인스턴스 Public IP
- `SSH_KEY` - SSH 키 파일 경로 (기본값: `~/.ssh/id_rsa`)

## 🧪 테스트 및 검증

### Python 스크립트 테스트
```bash
# 모든 Python 스크립트 컴파일 체크
python -m py_compile scripts/*.py

# 개별 스크립트 테스트
python scripts/build_and_push.py --help
python scripts/deploy_to_k8s.py --help
```

### Terraform 파일 검증
```bash
# Terraform 검증 스크립트 실행
python scripts/validate_terraform.py

# 또는 직접 Terraform 명령어 사용
cd terraform
terraform fmt -check -recursive    # 포맷팅 검사
terraform init -backend=false      # 초기화 (검증용)
terraform validate                  # 문법 및 유효성 검사
```

**Terraform 검증 단계:**
1. `terraform fmt -check`: 코드 포맷팅 검사
2. `terraform init -backend=false`: 초기화 (실제 백엔드 연결 없이)
3. `terraform validate`: 문법 및 유효성 검사

## 🔍 문제 해결

### DynamoDB 테이블을 찾을 수 없음
- Terraform이 완전히 적용되었는지 확인
- 테이블 이름이 올바른지 확인
- AWS 리전이 올바른지 확인

### kubectl 연결 오류
- kubeconfig 파일이 올바른지 확인
- EC2에서 Kubernetes 클러스터가 정상 작동하는지 확인
- `kubectl cluster-info` 명령어로 연결 테스트

### 이미지 푸시 실패 (Podman)
- ECR 리포지토리가 생성되었는지 확인
- AWS 자격 증명이 올바른지 확인
- `aws ecr get-login-password` 명령어로 ECR 로그인 테스트
- Podman이 설치되어 있고 실행 중인지 확인 (`podman --version`)
