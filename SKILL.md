## 스킬 이름

- **이름**: AuthCore Backend Helper
- **적용 범위**: `AuthCore` 레포 전체 (앱 코드, 테스트, k8s 매니페스트, 배포 스크립트, Terraform 서브 디렉토리 포함)
- **우선순위**: 높음 (AuthCore 관련 작업 요청 시 우선 적용)

---

## 이 스킬이 하는 일

- **목적**
  - AuthCore 인증 API 서비스에 대한 기능 추가, 버그 수정, 리팩토링, 테스트, 배포 흐름을 이해하고 일관된 방식으로 도와준다.
- **언제 사용해야 하는지**
  - 사용자가 AuthCore 로그인/회원가입/JWT/토큰 로테이션/배포/k3s/Podman 관련 작업을 요청할 때
  - AuthCore와 연관된 QuizNox/cluster-infra 설정을 참고해서 설명해야 할 때
- **하지 말아야 할 일**
  - `cluster-infra` 인프라 Terraform을 이 레포에서 직접 수정하려고 시도하지 않는다 (인프라 변경 가이드는 설명만 하고, 실제 코드는 `cluster-infra`에서 한다).
  - JWT 시크릿, AWS 자격 증명 등 민감 값은 절대 예시에도 실제 값처럼 쓰지 않는다.

---

## 프로젝트 개요

- **한 줄 요약**: 여러 플랫폼에 연동 가능한 인증(회원가입/로그인/JWT)을 제공하는 Fastify 기반 백엔드 API. DynamoDB를 쓰며 k3s(EC2) + Podman 환경에 배포된다.
- **주요 기술 스택**
  - Backend: Node.js + Fastify, `@fastify/jwt`, `@fastify/cors`, `@fastify/rate-limit`, `bcryptjs`, `jsonwebtoken`, `@aws-sdk v3`
  - DB: AWS DynamoDB
  - Infra: k3s (경량 Kubernetes), Podman(rootless), EC2, API Gateway V2
  - IaC/Automation: Terraform (인프라 자체는 `cluster-infra`), GitHub Actions, Python 배포 스크립트
- **중요 디렉토리**
  - `src/` – 서버 엔트리포인트, 라우트, 미들웨어, 서비스, 유틸
  - `tests/` – unit / integration 테스트, fixtures, Jest 설정
  - `k8s/` – `deployment.yaml`, `service.yaml`, `namespace.yaml` 등 AuthCore용 Kubernetes 매니페스트
  - `scripts/` – `build_and_push.py`, `setup_k8s.py`, `deploy_to_k8s.py`, `update_apigateway_backend.py` 등 배포 스크립트
  - `terraform/` – AuthCore에서 사용하는 일부 Terraform 설정(필요 시 참고만; 공용 인프라는 `cluster-infra` 기준)
  - `docs/` – API 문서, 배포 가이드, 테스트 예제, 리소스 요구사항 등

---

## 작업 방식 가이드

- **코드 스타일 / 규칙**
  - Node.js + Fastify 코드 작성 시, 기존 라우트/서비스 구조(`src/routes`, `src/services`, `src/middleware`)를 따라간다.
  - 에러 처리는 공통 미들웨어(`src/middleware/errorHandler.js`)를 활용하고, 직접 `res.send`로 섞어서 쓰지 않도록 한다.
  - 인증 관련 로직(JWT 발급/검증/리프레시)은 `authService`, `authMiddleware`, Fastify JWT 플러그인 패턴을 최대한 재사용한다.
- **테스트**
  - Jest 기반 테스트를 사용하며, 새로운 도메인 로직을 추가할 때는 아래를 기본으로 한다.
    - **단위 테스트**: `tests/unit` 아래에 파일 추가
    - **통합 테스트**: `tests/integration` 아래에 엔드투엔드 관점 테스트 추가
  - 스킬은 다음 스크립트를 우선 제안한다.
    - 전체: `npm test`
    - 유닛: `npm run test:unit`
    - 통합: `npm run test:integration` 또는 `npm run test:integration:real-db` (실제 DB 사용 옵션이 필요한 경우)
- **커밋 / 브랜치 규칙 (예시 기본값, 레포 규칙과 충돌 시 레포 규칙 우선)**
  - 브랜치는 기능 단위로 `feat/...`, `fix/...`, `chore/...` 등을 권장한다.
  - 커밋 메시지는 변경 의도 중심으로 짧게 요약한다 (예: `feat: add refresh token rotation`).

---

## 도구 / 커맨드

- **로컬 개발**
  - 의존성 설치: `npm install`
  - 환경변수 템플릿에서 복사: `cp env.example .env`
  - 개발 서버: `npm run dev` (기본적으로 `IS_LOCAL=true`, `PORT=4000` 등 로컬 플래그 포함)
- **테스트**
  - `npm test` – 전체 테스트
  - `npm run test:unit` – 유닛 테스트
  - `npm run test:integration` – 통합 테스트 (기본)
  - `npm run test:integration:real-db` – 실제 DynamoDB와 연결해서 통합 테스트 (USE_REAL_DB=true)
  - `npm run test:coverage` – 커버리지 리포트
- **빌드/배포 (설명 위주)**
  - 컨테이너 빌드 및 ECR 푸시, k3s 배포, API Gateway 백엔드 연결은 GitHub Actions와 Python 스크립트 조합으로 동작한다.
  - 수동 플로우 예시(설명 시 인용):
    - `python scripts/build_and_push.py`
    - `python scripts/setup_k8s.py`
    - `python scripts/deploy_to_k8s.py`
    - `python scripts/update_apigateway_backend.py`

---

## 제약 사항 / 주의점

- **보안 / 비밀 정보**
  - JWT 시크릿, AWS 자격 증명, DB 이름 등은 코드에 하드코딩하지 않는다.
  - 예시로 값을 보여줄 때는 `JWT_SECRET=***` 같은 형식으로 마스킹하거나 가짜 값을 사용한다.
  - GitHub Secrets 이름(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `SSH_PRIVATE_KEY` 등)은 정확히 유지하되 값은 절대 노출하지 않는다.
- **아키텍처 제약**
  - DB 접근은 DynamoDB 클라이언트를 감싸는 서비스 계층을 통해서만 수행하고, 라우트에서 직접 SDK를 호출하지 않는다.
  - 인증/인가 로직은 미들웨어/플러그인 계층에 두고, 핸들러 안쪽에서는 이미 인증된 사용자 정보만 사용하는 방향을 유지한다.
  - 인프라 자체(VPC, EC2, ECR, DynamoDB, API Gateway 등)를 새로 만들거나 크게 바꾸는 제안은 `cluster-infra` 레포를 기준으로 설명한다.

---

## 답변 스타일

- **언어**: 기본은 한국어, 필요 시 코드/리소스 이름은 영어 그대로 사용
- **톤**: 친절하지만, 운영/보안 관련해서는 단호하게 위험성을 짚어 준다.
- **길이**:
  - 구현/코드 요청: 코드 위주로, 필요한 부분에만 간단한 설명
  - 아키텍처/운영 질문: 다이어그램/구조를 요약하고, 문서(`README.md`, `docs/`)를 함께 가리켜 준다.

---

## 예시 시나리오

- **예시 1 – 로그인 API 수정**
  - 사용자가 “로그인 응답에 추가 필드를 넣어줘”라고 하면:
    - 관련 라우트(`src/routes/authRoutes.js` 등)를 찾는다.
    - 서비스/미들웨어 구조를 유지하면서 응답 스키마를 확장한다.
    - 최소한의 단위/통합 테스트를 함께 제안한다.
- **예시 2 – JWT 만료 정책 변경**
  - 사용자가 “access token 만료 시간을 늘려줘”라고 하면:
    - JWT 발급 로직이 있는 서비스/플러그인 파일을 찾는다.
    - 기존 정책(만료 시간·리프레시 전략)을 파악한 뒤, 보안 트레이드오프를 같이 설명한다.
    - 변경 후 영향 범위(테스트, 문서, 클라이언트 사용법)를 함께 안내한다.
- **예시 3 – 배포 이슈 디버깅**
  - 사용자가 “k3s에 배포했는데 502가 떠”라고 하면:
    - k3s Deployment/Service, API Gateway 설정, Health Check, 로그 확인 순서로 단계별 체크리스트를 제안한다.
    - `cluster-infra`에서 제공하는 출력값(EC2 IP, API Gateway URL 등)을 어떻게 확인할지 안내한다.

