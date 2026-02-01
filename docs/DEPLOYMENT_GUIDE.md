# 🚀 AuthCore 배포 가이드 (통합)

## 📋 개요

AuthCore를 **Terraform + k3s (경량 Kubernetes) + Podman** 아키텍처로 배포하는 완전한 가이드입니다.

### 아키텍처

```
API Gateway (기존 유지) 
    ↓
EC2 (t3.small) 
    ↓
k3s (경량 Kubernetes)
    ↓
Pod (AuthCore 애플리케이션)
    ↓
DynamoDB (기존 유지)
```

### 기술 스택

- **인프라**: Terraform
- **컨테이너 오케스트레이션**: k3s (경량 Kubernetes)
- **컨테이너 런타임**: Podman (rootless, daemonless)
- **이미지 레지스트리**: AWS ECR
- **데이터베이스**: DynamoDB (기존 유지)
- **API Gateway**: AWS API Gateway V2 (기존 엔드포인트 유지)
- **비밀 관리**: AWS Secrets Manager

### 비용

- **EC2**: t3.small (2GB RAM) - ~$15-20/월
- **기타**: DynamoDB, API Gateway, ECR, S3 등 (기존 유지)

---

## 🎯 사전 준비

### 1. 필수 도구 설치

```bash
# Terraform
brew install terraform  # macOS
# 또는 https://www.terraform.io/downloads

# kubectl
brew install kubectl  # macOS

# Podman (macOS)
brew install podman
podman machine init
podman machine start

# AWS CLI
brew install awscli  # macOS
aws configure
```

### 2. AWS 자격 증명 설정

```bash
aws configure
# AWS Access Key ID
# AWS Secret Access Key
# Default region: ap-northeast-2
# Default output format: json
```

### 3. SSH 키 페어 생성

```bash
# AWS 콘솔에서 생성하거나
aws ec2 create-key-pair \
  --key-name your-key-pair-name \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/your-key-pair-name.pem

chmod 400 ~/.ssh/your-key-pair-name.pem
```

---

## 📦 1단계: Terraform 인프라 배포

### 1-1. Terraform 변수 설정

```bash
cd terraform

# terraform.tfvars 파일 생성/수정
cat > terraform.tfvars <<EOF
existing_api_gateway_name = ""           # 기존 API Gateway ID (있는 경우)
ec2_instance_type = "t3.small"            # 최소 비용
key_pair_name = "your-key-pair-name"      # SSH 키 페어 이름
EOF
```

### 1-2. 기존 리소스 Import (선택사항)

기존 DynamoDB 테이블이 있는 경우:

```bash
# 자동 import
python scripts/import_existing_resources.py

# 또는 수동 import
terraform import aws_dynamodb_table.users AuthCore_Users
terraform import aws_dynamodb_table.refresh_tokens AuthCore_RefreshTokens
```

### 1-3. 인프라 배포

```bash
# Terraform 초기화
terraform init

# 계획 확인
terraform plan

# 인프라 생성 (k3s 자동 설치됨)
terraform apply

# 출력값 확인
terraform output
```

**생성되는 리소스:**
- VPC 및 서브넷
- 보안 그룹 (SSH, HTTP, HTTPS, k3s API Server)
- EC2 인스턴스 (k3s 자동 설치)
- ECR 리포지토리
- S3 버킷
- Secrets Manager (JWT Secret)
- DynamoDB 테이블 (기존 것 사용 또는 새로 생성)

**예상 시간**: 3-5분

---

## 🔧 2단계: k3s 클러스터 확인

### 2-1. EC2 접속 및 k3s 상태 확인

```bash
# EC2 Public IP 확인
EC2_IP=$(cd terraform && terraform output -raw ec2_public_ip)
echo "EC2 IP: $EC2_IP"

# SSH 접속
ssh -i ~/.ssh/your-key-pair-name.pem ubuntu@$EC2_IP

# k3s 상태 확인
sudo systemctl status k3s

# kubectl로 노드 확인
export KUBECONFIG=/home/ubuntu/.kube/config
kubectl get nodes
```

**정상 출력 예시:**
```
NAME           STATUS   ROLES                  AGE   VERSION
ip-10-0-1-217  Ready    control-plane,master   2m    v1.28.x+k3s1
```

### 2-2. 로컬 kubeconfig 설정

```bash
# 방법 1: 자동 스크립트 (권장)
export EC2_IP=$(cd terraform && terraform output -raw ec2_public_ip)
export SSH_KEY=~/.ssh/your-key-pair-name.pem
python scripts/setup_k8s.py

# 방법 2: 수동 복사
scp -i ~/.ssh/your-key-pair-name.pem \
    ubuntu@$EC2_IP:~/.kube/config ~/.kube/config
chmod 600 ~/.kube/config

# server 주소를 Public IP로 변경
sed -i '' "s|127.0.0.1|$EC2_IP|g" ~/.kube/config

# 연결 확인
kubectl get nodes
```

---

## 🐳 3단계: Podman으로 이미지 빌드 및 푸시

### 3-1. 환경 변수 설정

```bash
export AWS_REGION="ap-northeast-2"
export ENVIRONMENT="prod"
export IMAGE_TAG="latest"
```

### 3-2. 이미지 빌드 및 ECR 푸시

```bash
# Podman으로 이미지 빌드 및 ECR 푸시
python scripts/build_and_push.py
```

**수행 작업:**
- ECR 로그인 (Podman)
- Dockerfile로 이미지 빌드 (Podman)
- 이미지 태그
- ECR에 푸시
- 이미지 URI 저장 (`.image_uri` 파일)

---

## ☸️ 4단계: Kubernetes 배포

### 4-1. 환경 변수 설정

```bash
export KUBECONFIG=~/.kube/config
export NAMESPACE="authcore"
export AWS_REGION="ap-northeast-2"
export USERS_TABLE="AuthCore_Users"
export REFRESH_TOKENS_TABLE="AuthCore_RefreshTokens"

# JWT_SECRET은 Secrets Manager에서 자동으로 가져옴 (설정 불필요)
```

### 4-2. Kubernetes 배포

```bash
python scripts/deploy_to_k8s.py
```

**수행 작업:**
- 네임스페이스 생성 (`authcore`)
- ECR Secret 생성 (이미지 pull 권한)
- Kubernetes Secret 생성 (JWT_SECRET - Secrets Manager에서 자동 가져옴)
- ConfigMap 생성 (환경 변수)
- Deployment 배포 (Pod 2개)
- Service 배포 (LoadBalancer 타입)
- 배포 상태 확인

### 4-3. 배포 상태 확인

```bash
# Pod 상태 확인
kubectl get pods -n authcore

# Service 상태 확인
kubectl get svc -n authcore

# 배포 로그 확인
kubectl logs -n authcore -l app=authcore-api --tail=50
```

**정상 출력 예시:**
```
NAME                           READY   STATUS    RESTARTS   AGE
authcore-api-xxxxx-xxxxx       1/1     Running   0          1m
authcore-api-xxxxx-xxxxx       1/1     Running   0          1m

NAME           TYPE           CLUSTER-IP      EXTERNAL-IP     PORT(S)        AGE
authcore-api   LoadBalancer   10.43.x.x      <pending>       80:xxxxx/TCP   1m
```

---

## 🌐 5단계: API Gateway 백엔드 연결

### 5-1. 백엔드 URL 확인

k3s의 LoadBalancer는 klipper-lb를 사용하며, 실제로는 NodePort처럼 동작합니다.

```bash
# Service의 NodePort 확인
kubectl get svc authcore-api -n authcore -o jsonpath='{.spec.ports[0].nodePort}'

# EC2 Public IP 확인
cd terraform
terraform output ec2_public_ip
```

### 5-2. API Gateway Integration 업데이트

```bash
# 자동으로 백엔드 URL을 가져와서 API Gateway Integration 업데이트
python scripts/update_apigateway_backend.py
```

**수행 작업:**
- Kubernetes Service에서 백엔드 URL 가져오기 (LoadBalancer 또는 NodePort)
- API Gateway Integration 생성/업데이트
- API Gateway Routes 생성/확인

**참고**: 기존 API Gateway 엔드포인트는 유지됩니다. 백엔드만 k3s로 연결됩니다.

---

## 🧪 6단계: 배포 검증

### 6-1. API 테스트

```bash
# API Gateway 엔드포인트 확인 (실제 API Gateway ID로 변경)
API_URL="https://<YOUR_API_GATEWAY_ID>.execute-api.ap-northeast-2.amazonaws.com"

# Health check
curl $API_URL/health

# 회원가입
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# 로그인
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

### 6-2. 초기 데이터 삽입 (선택사항)

```bash
# DynamoDB에 테스트 계정 삽입
export AWS_REGION="ap-northeast-2"
export USERS_TABLE_NAME="AuthCore_Users"
python scripts/seed_data.py
```

**기본 테스트 계정:**
- `admin` / `admin123`
- `testuser` / `testpass123`
- `demo` / `demo123`

**참고**: 기존 계정이 있으면 덮어쓰지 않습니다.

---

## 🔧 k3s 수동 설정 (문제 해결 시)

자동 설치가 실패한 경우 수동으로 설정할 수 있습니다.

### k3s 수동 설치

```bash
# EC2에 SSH 접속
ssh -i ~/.ssh/your-key-pair-name.pem ubuntu@$EC2_IP

# IP 주소 확인
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

# k3s 설치
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_EXEC="--tls-san $PUBLIC_IP --node-ip $PRIVATE_IP --bind-address $PRIVATE_IP" sh -

# k3s 상태 확인
sudo systemctl status k3s

# kubeconfig 설정
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown ubuntu:ubuntu ~/.kube/config
sed -i "s|127.0.0.1|$PUBLIC_IP|g" ~/.kube/config

# 연결 확인
export KUBECONFIG=~/.kube/config
kubectl get nodes
```

---

## 🔍 문제 해결

### 문제 1: kubectl 연결 실패

**증상**: `connection refused` 또는 `operation not permitted`

**해결:**
```bash
# kubeconfig의 server 주소 확인
cat ~/.kube/config | grep server

# Public IP로 변경 (필요시)
EC2_IP=$(cd terraform && terraform output -raw ec2_public_ip)
sed -i '' "s|127.0.0.1|$EC2_IP|g" ~/.kube/config
sed -i '' "s|10\.0\.[0-9]\+\.[0-9]\+|$EC2_IP|g" ~/.kube/config

# 연결 테스트
kubectl get nodes
```

### 문제 2: Pod가 시작되지 않음

**증상**: `ImagePullBackOff` 또는 `CrashLoopBackOff`

**해결:**
```bash
# Pod 상세 정보 확인
kubectl describe pod -n authcore <pod-name>

# Pod 로그 확인
kubectl logs -n authcore <pod-name>

# ECR Secret 확인
kubectl get secrets -n authcore | grep ecr-registry-secret

# 이미지 URI 확인
cat .image_uri
```

### 문제 3: LoadBalancer가 pending 상태

**증상**: `kubectl get svc`에서 EXTERNAL-IP가 `<pending>`

**해결:**
k3s의 LoadBalancer는 klipper-lb를 사용하며, 실제로는 NodePort처럼 동작합니다. 스크립트가 자동으로 EC2 IP:NodePort로 연결합니다.

```bash
# NodePort 확인
kubectl get svc authcore-api -n authcore -o jsonpath='{.spec.ports[0].nodePort}'

# 직접 테스트
EC2_IP=$(cd terraform && terraform output -raw ec2_public_ip)
NODEPORT=$(kubectl get svc authcore-api -n authcore -o jsonpath='{.spec.ports[0].nodePort}')
curl http://$EC2_IP:$NODEPORT/health
```

### 문제 4: 비밀번호가 일치하지 않음

**증상**: 기존 계정으로 로그인 실패

**원인**: 
- `seed_data.py`가 기존 계정을 덮어썼을 수 있음 (이미 수정됨)
- 기존 계정의 비밀번호 해시 형식이 다를 수 있음

**해결:**
```bash
# 새 계정으로 등록
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "password": "newpass123"}'
```

### 문제 5: 메모리 부족

**증상**: 시스템 Pod가 계속 재시작

**해결:**
- t3.small (2GB)는 k3s에 최소 요구사항입니다
- 안정적인 운영을 위해서는 t3.medium (4GB) 권장
- `terraform.tfvars`에서 `ec2_instance_type = "t3.medium"`으로 변경 후 `terraform apply`

---

## 📊 모니터링 및 관리

### 리소스 사용량 확인

```bash
# 노드 리소스 사용량
kubectl top nodes

# Pod 리소스 사용량
kubectl top pods -n authcore

# 전체 리소스 상태
kubectl get all -n authcore
```

### 로그 확인

```bash
# 애플리케이션 로그
kubectl logs -n authcore -l app=authcore-api --tail=100 -f

# k3s 로그 (EC2에서)
ssh -i ~/.ssh/your-key-pair-name.pem ubuntu@$EC2_IP
sudo journalctl -xeu k3s -n 100 --no-pager
```

### 배포 업데이트

```bash
# 새 이미지 빌드 및 푸시
python scripts/build_and_push.py

# Kubernetes 배포 업데이트
python scripts/deploy_to_k8s.py

# 롤링 업데이트 확인
kubectl rollout status deployment/authcore-api -n authcore
```

---

## 🔐 보안 고려사항

### 1. SSH 접근 제한

프로덕션 환경에서는 보안 그룹에서 SSH 포트(22)를 특정 IP로 제한하세요.

### 2. JWT Secret 관리

- Secrets Manager에 저장됨
- 환경 변수로 직접 노출하지 않음
- 정기적으로 로테이션 권장

### 3. API Gateway 접근 제한

프로덕션 환경에서는 CORS 설정을 특정 도메인으로 제한하세요.

---

## 💰 비용 최적화

### 현재 구성 (최소 비용)

- **EC2**: t3.small (2GB) - ~$15-20/월
- **k3s**: 경량으로 메모리 효율적
- **Podman**: 데몬 없이 실행되어 리소스 절약

### 권장 구성 (안정적)

- **EC2**: t3.medium (4GB) - ~$30-35/월
- 더 안정적인 운영 가능
- 피크 사용량 대비 여유 공간 확보

---

## 📚 참고 문서

- **API 문서**: `docs/API.md`
- **k3s 공식 문서**: https://k3s.io/
- **Podman 공식 문서**: https://podman.io/

---

## ✅ 배포 체크리스트

- [ ] Terraform 인프라 배포 완료
- [ ] k3s 클러스터 정상 작동 확인
- [ ] 로컬 kubeconfig 설정 완료
- [ ] Podman으로 이미지 빌드 및 ECR 푸시 완료
- [ ] Kubernetes 배포 완료 (Pod Running 상태)
- [ ] API Gateway 백엔드 연결 완료
- [ ] API 테스트 성공
- [ ] 초기 데이터 삽입 (선택사항)

---

**배포 완료!** 🎉

이제 API Gateway 엔드포인트를 통해 AuthCore 서비스를 사용할 수 있습니다.
