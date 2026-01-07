# Kubernetes 매니페스트

이 디렉토리는 AuthCore 애플리케이션을 Kubernetes에 배포하기 위한 매니페스트 파일들을 포함합니다.

## 파일 구조

- `namespace.yaml` - authcore 네임스페이스
- `deployment.yaml` - 애플리케이션 Deployment (Pod 2개)
- `service.yaml` - LoadBalancer 타입 Service

## 사용 방법

### 1. 네임스페이스 생성
```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Secret 생성 (JWT_SECRET)
```bash
kubectl create secret generic authcore-secrets \
  --from-literal=JWT_SECRET=your-secret-key \
  --namespace=authcore
```

### 3. ConfigMap 생성
```bash
kubectl create configmap authcore-config \
  --from-literal=AWS_REGION=ap-northeast-2 \
  --from-literal=NODE_ENV=prod \
  --from-literal=USERS_TABLE=AuthCore_Users \
  --from-literal=REFRESH_TOKENS_TABLE=AuthCore_RefreshTokens \
  --namespace=authcore
```

### 4. Deployment 배포
```bash
# IMAGE_URI 환경 변수 설정 필요
export IMAGE_URI=123456789.dkr.ecr.ap-northeast-2.amazonaws.com/authcore-prod:latest
envsubst < k8s/deployment.yaml | kubectl apply -f -
```

### 5. Service 배포
```bash
kubectl apply -f k8s/service.yaml
```

## 자동 배포

Python 스크립트를 사용하여 자동으로 배포할 수 있습니다:

```bash
# 1. 이미지 빌드 및 푸시
python scripts/build_and_push.py

# 2. Kubernetes 배포
python scripts/deploy_to_k8s.py
```

## 리소스 요구사항

- **CPU**: Pod당 200m 요청, 500m 제한
- **Memory**: Pod당 256Mi 요청, 512Mi 제한
- **Replicas**: 2개 (고가용성)

## 헬스체크

- **Liveness Probe**: `/health` 엔드포인트, 30초 후 시작, 10초마다 체크
- **Readiness Probe**: `/health` 엔드포인트, 10초 후 시작, 5초마다 체크

## LoadBalancer

Service는 LoadBalancer 타입으로 설정되어 있어 외부에서 접근 가능합니다.
LoadBalancer URL은 배포 후 다음 명령어로 확인:

```bash
kubectl get svc authcore-api -n authcore
```

