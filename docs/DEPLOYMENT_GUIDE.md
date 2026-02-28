# AuthCore 배포 가이드

## 사전 조건

- **인프라가 이미 프로비저닝되어 있어야 합니다** → [cluster-infra](../../cluster-infra) 저장소 참고
- AWS CLI 인증이 설정되어 있어야 합니다 (`aws configure`)
- Python 3.11+ / kubectl / Podman 설치

```bash
pip install -r requirements.txt
```

---

## 1단계: kubeconfig 설정

EC2(k3s 노드)에서 kubeconfig를 복사합니다.

```bash
# 자동 (권장)
export EC2_IP="<EC2 Public IP>"
export SSH_KEY=~/.ssh/your-key.pem
python scripts/setup_k8s.py

# 수동
scp -i ~/.ssh/your-key.pem ubuntu@$EC2_IP:~/.kube/config ~/.kube/config
sed -i '' "s|127.0.0.1|$EC2_IP|g" ~/.kube/config
kubectl get nodes
```

---

## 2단계: 이미지 빌드 및 ECR 푸시

```bash
export AWS_REGION="ap-northeast-2"
export ENVIRONMENT="prod"
export IMAGE_TAG="latest"
python scripts/build_and_push.py
```

---

## 3단계: Kubernetes 배포

```bash
export KUBECONFIG=~/.kube/config
export NAMESPACE="authcore"
export AWS_REGION="ap-northeast-2"
export USERS_TABLE="AuthCore_Users"
export REFRESH_TOKENS_TABLE="AuthCore_RefreshTokens"
python scripts/deploy_to_k8s.py
```

수행 내용:
- 네임스페이스 생성 (`authcore`)
- ECR Secret / Kubernetes Secret (JWT_SECRET - Secrets Manager에서 자동 조회)
- ConfigMap / Deployment (Pod 2개) / Service

---

## 4단계: API Gateway 백엔드 연결

```bash
export EC2_PUBLIC_IP="<EC2 Public IP>"
export AWS_REGION="ap-northeast-2"
export API_GATEWAY_ID="<API Gateway ID>"
python scripts/update_apigateway_backend.py
```

---

## 5단계: 검증

```bash
# Pod 상태
kubectl get pods -n authcore

# Health check (API Gateway 경유)
API_URL="https://<API_GATEWAY_ID>.execute-api.ap-northeast-2.amazonaws.com"
curl $API_URL/health
```

---

## CI/CD 자동 배포

`main` 브랜치에 push하면 GitHub Actions가 위 2~4단계를 자동으로 수행합니다.
필요한 GitHub Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `SSH_PRIVATE_KEY`

---

## 문제 해결

### kubectl 연결 실패
kubeconfig의 `server` 주소가 EC2 Public IP인지 확인합니다.

### ImagePullBackOff
ECR Secret이 올바른지, 이미지 URI가 정확한지 확인합니다.

```bash
kubectl describe pod -n authcore <pod-name>
kubectl get secrets -n authcore | grep ecr
```

### Pod CrashLoopBackOff
환경 변수(DynamoDB 테이블명, JWT_SECRET 등)가 누락되지 않았는지 확인합니다.

```bash
kubectl logs -n authcore <pod-name>
```

### 메모리 부족
t3.small (2GB)은 k3s 최소 요구사항입니다. 안정적 운영은 t3.medium (4GB) 권장.
자세한 내용은 [리소스 요구사항](./RESOURCE_REQUIREMENTS.md)을 참고하세요.
