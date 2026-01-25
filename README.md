# 🔐 AuthCore

여러 플랫폼에 연동 가능한 인증 서비스를 제공하는 컨테이너 오케스트레이션 기반 API입니다.  
DynamoDB를 백엔드 DB로 사용하며, **k3s (경량 Kubernetes) + Podman + EC2**에 배포됩니다.

---

## 🏗️ 아키텍처

```
API Gateway (AWS API Gateway V2)
    ↓
EC2 (t3.small)
    ↓
k3s (경량 Kubernetes)
    ↓
Pod (AuthCore 애플리케이션)
    ↓
DynamoDB
```

---

## 🛠️ 기술 스택

### 애플리케이션

- **Fastify** (`^4.21.0`) – 고성능 Node.js 웹 프레임워크
- **DynamoDB** – 무중단 NoSQL 데이터베이스
- **JWT** – JSON Web Token 기반 인증
- **bcryptjs** – 비밀번호 해싱
- **@aws-sdk v3** – 최신 AWS SDK (DynamoDB client)

### 인프라

- **Terraform** – Infrastructure as Code
- **k3s** – 경량 Kubernetes (컨테이너 오케스트레이션)
- **Podman** – rootless, daemonless 컨테이너 런타임
- **AWS ECR** – 컨테이너 이미지 레지스트리
- **AWS API Gateway V2** – API 엔드포인트
- **AWS Secrets Manager** – 비밀 관리

## 📚 문서

- **[배포 가이드](./docs/DEPLOYMENT_GUIDE.md)** – 상세한 배포 절차 및 문제 해결
- **[API 문서](./docs/API.md)** – API 엔드포인트 및 사용법
- **[API 테스트 예제](./docs/API_TEST_EXAMPLES.md)** – API 테스트 예제
- **[워크플로우 가이드](./.github/WORKFLOW_GUIDE.md)** – GitHub Actions CI/CD 가이드
- **[리소스 요구사항](./docs/RESOURCE_REQUIREMENTS.md)** – 인프라 리소스 요구사항

---

## 🔧 개발

### 로컬 개발 환경

```bash
# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 개발 서버 실행
npm run dev
```

### 테스트

```bash
# 모든 테스트 실행
npm test

# Unit 테스트만
npm run test:unit

# Integration 테스트만
npm run test:integration

# 커버리지 리포트
npm run test:coverage
```

---

## 🎯 주요 기능

- ✅ 사용자 회원가입 및 로그인
- ✅ JWT 기반 인증
- ✅ Refresh Token 지원
- ✅ 비밀번호 해싱 (bcrypt)
- ✅ Rate Limiting
- ✅ CORS 지원
- ✅ Health Check 엔드포인트

---

## 💰 비용

- **EC2**: t3.small (2GB RAM) - ~$15-20/월
- **기타**: DynamoDB, API Gateway, ECR, S3 등 (사용량 기반)

---

## 🔐 보안

- JWT Secret은 AWS Secrets Manager에 저장
- 환경 변수는 절대 코드에 하드코딩하지 않음
- SSH 키는 GitHub Secrets로 관리
- 컨테이너는 rootless 모드로 실행 (Podman)
