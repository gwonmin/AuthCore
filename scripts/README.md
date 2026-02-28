# Scripts

AuthCore 앱 빌드 및 배포에 사용되는 스크립트입니다.
인프라 프로비저닝은 [cluster-infra](../../cluster-infra) 저장소에서 관리합니다.

## 스크립트 목록

### `build_and_push.py`
Podman으로 이미지를 빌드하고 ECR에 푸시합니다.

```bash
export AWS_REGION="ap-northeast-2"
export ENVIRONMENT="prod"
export IMAGE_TAG="latest"
python scripts/build_and_push.py
```

### `deploy_to_k8s.py`
Kubernetes(k3s)에 애플리케이션을 배포합니다. JWT_SECRET은 Secrets Manager에서 자동으로 가져옵니다.

```bash
export KUBECONFIG="~/.kube/config"
export NAMESPACE="authcore"
export IMAGE_URI="123456789.dkr.ecr.ap-northeast-2.amazonaws.com/authcore-prod:latest"
python scripts/deploy_to_k8s.py
```

### `setup_k8s.py`
EC2(k3s 노드)에서 kubeconfig를 복사하여 로컬 kubectl 접근을 설정합니다.

```bash
export EC2_IP="1.2.3.4"
export SSH_KEY="~/.ssh/id_rsa"
python scripts/setup_k8s.py
```

### `update_apigateway_backend.py`
Kubernetes Service 엔드포인트를 API Gateway 백엔드로 연결합니다.

```bash
export EC2_PUBLIC_IP="1.2.3.4"
export AWS_REGION="ap-northeast-2"
export API_GATEWAY_ID="abc123"
python scripts/update_apigateway_backend.py
```

## 사전 요구사항

```bash
pip install -r requirements.txt
aws configure
```
