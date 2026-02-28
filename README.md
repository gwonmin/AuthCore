# AuthCore

여러 플랫폼에 연동 가능한 인증 서비스를 제공하는 컨테이너 오케스트레이션 기반 API입니다.
DynamoDB를 백엔드 DB로 사용하며, **k3s (경량 Kubernetes) + Podman + EC2**에 배포됩니다.

> 인프라(VPC, EC2, ECR, DynamoDB 등)는 [cluster-infra](../cluster-infra) 저장소에서 Terraform으로 관리합니다.
> 이 저장소는 **앱 테스트 / 빌드 / 배포**만 담당합니다.

---

## 아키텍처

```
API Gateway (AWS API Gateway V2)
    ↓
EC2 (k3s)
    ↓
Pod (AuthCore 애플리케이션)
    ↓
DynamoDB
```

---

## 기술 스택

- **Fastify** – 고성능 Node.js 웹 프레임워크
- **DynamoDB** – NoSQL 데이터베이스
- **JWT** – JSON Web Token 기반 인증
- **bcryptjs** – 비밀번호 해싱
- **@aws-sdk v3** – AWS SDK

---

## 주요 기능

- 사용자 회원가입 및 로그인
- JWT 기반 인증 (Access + Refresh Token)
- 비밀번호 해싱 (bcrypt)
- Rate Limiting / CORS
- Health Check 엔드포인트

---

## 개발

### 로컬 환경

```bash
npm install
cp env.example .env
npm run dev
```

### 테스트

```bash
npm test              # 전체
npm run test:unit     # Unit
npm run test:integration  # Integration
npm run test:coverage     # 커버리지
```

---

## CI/CD

GitHub Actions (`ci-cd.yml`)가 다음 파이프라인을 자동 실행합니다.

| 단계 | 트리거 | 내용 |
|------|--------|------|
| **test** | 모든 push / PR | Unit + Integration 테스트 |
| **build-and-push** | `main` push | Podman 빌드 → ECR 푸시 |
| **deploy** | `main` push | k3s 클러스터에 배포, API Gateway 연결 |

### 필요한 GitHub Secrets

| 이름 | 설명 |
|------|------|
| `AWS_ACCESS_KEY_ID` | AWS 액세스 키 |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 키 |
| `SSH_PRIVATE_KEY` | EC2 접속용 SSH 프라이빗 키 |

---

## 문서

- [배포 가이드](./docs/DEPLOYMENT_GUIDE.md)
- [API 문서](./docs/API.md)
- [API 테스트 예제](./docs/API_TEST_EXAMPLES.md)
- [리소스 요구사항](./docs/RESOURCE_REQUIREMENTS.md)

---

## 보안

- JWT Secret은 AWS Secrets Manager에 저장
- 환경 변수는 절대 코드에 하드코딩하지 않음
- SSH 키는 GitHub Secrets로 관리
- 컨테이너는 rootless 모드로 실행 (Podman)
