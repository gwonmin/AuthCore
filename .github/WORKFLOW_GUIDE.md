# GitHub Actions CI/CD 워크플로우 가이드

## 📋 개요

이 문서는 AuthCore 프로젝트의 GitHub Actions CI/CD 워크플로우에 대한 종합 가이드입니다.

### 워크플로우 구조

```
ci-cd.yml
├── test job (모든 브랜치/PR)
│   ├── Node.js 23.10.0에서 테스트 실행
│   ├── Unit 테스트
│   ├── Integration 테스트
│   └── 커버리지 리포트 생성
│
├── build-and-push job (needs: test, main 브랜치만)
│   ├── Podman으로 이미지 빌드
│   └── ECR에 이미지 푸시
│
└── deploy job (needs: build-and-push, main 브랜치만)
    ├── kubeconfig 설정
    ├── Kubernetes 배포 (k3s)
    ├── API Gateway 백엔드 업데이트
    └── 배포 검증
```

---

## 🔐 GitHub Secrets 설정

### 필수 Secrets (3개만!)

GitHub 저장소의 **Settings → Secrets and variables → Actions**에서 다음 Secrets를 등록해야 합니다:

| Secret 이름             | 설명                            | 예시                                       | 필수 여부 |
| ----------------------- | ------------------------------- | ------------------------------------------ | --------- |
| `AWS_ACCESS_KEY_ID`     | AWS 액세스 키 ID                | `AKIAIOSFODNN7EXAMPLE`                     | ✅ 필수   |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 액세스 키            | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | ✅ 필수   |
| `SSH_PRIVATE_KEY`       | EC2 인스턴스 접근용 SSH 개인 키 | `-----BEGIN RSA PRIVATE KEY-----...`       | ✅ 필수   |

### 자동 조회되는 값들 (Secrets 불필요)

다음 값들은 워크플로우가 자동으로 조회하므로 GitHub Secrets에 등록할 필요가 없습니다:

| 값 이름               | 자동 조회 방법             | 워크플로우 단계              | 설명                                                     |
| --------------------- | -------------------------- | ---------------------------- | -------------------------------------------------------- |
| `EC2_PUBLIC_IP`       | Terraform output → AWS CLI | `Get infrastructure values`  | EC2 인스턴스 Public IP 자동 조회                         |
| `API_GATEWAY_ID`      | Terraform output → AWS CLI | `Get infrastructure values`  | API Gateway ID 자동 조회 (authcore 이름 패턴 검색)       |
| `JWT_SECRET`          | Secrets Manager            | `Deploy to Kubernetes (k3s)` | `deploy_to_k8s.py`가 자동으로 Secrets Manager에서 가져옴 |
| `SECRETS_MANAGER_ARN` | Terraform output → AWS CLI | `Get infrastructure values`  | Secrets Manager ARN 자동 조회                            |

**🎉 개선 사항**: 이제 **필수 Secrets가 3개만** 필요합니다!

---

## 📝 환경 변수

워크플로우 파일의 `env` 섹션에 정의된 환경 변수:

```yaml
env:
  AWS_REGION: ap-northeast-2 # AWS 리전
  ENVIRONMENT: prod # 환경 이름 (ECR 리포지토리 이름에 사용)
```

| 변수 이름     | 기본값           | 설명                                        | 수정 가능 |
| ------------- | ---------------- | ------------------------------------------- | --------- |
| `AWS_REGION`  | `ap-northeast-2` | AWS 리전                                    | ✅ 가능   |
| `ENVIRONMENT` | `prod`           | 환경 이름 (ECR 리포지토리: `authcore-prod`) | ✅ 가능   |

---

## 🚀 워크플로우 실행 시나리오

### 1. Pull Request 생성/업데이트

```
test job 실행
  ↓
테스트 결과 확인
```

- **실행되는 job**: `test`만
- **목적**: 코드 변경 사항 검증
- **결과**: 테스트 통과 여부 확인

### 2. develop 브랜치에 push

```
test job 실행
  ↓
테스트 결과 확인
```

- **실행되는 job**: `test`만
- **목적**: 개발 브랜치 코드 검증

### 3. main 브랜치에 push

```
test job
  ↓ (성공 시)
build-and-push job
  ↓ (성공 시)
deploy job
```

- **실행되는 job**: `test` → `build-and-push` → `deploy` (순차 실행)
- **목적**: 프로덕션 배포
- **조건**: 모든 이전 job이 성공해야 다음 job 실행

---

## 🔄 자동 조회 로직

워크플로우는 다음 순서로 값을 조회합니다:

1. **Terraform output 시도** (가장 빠름)
   - `terraform output -raw <output_name>` 실행
   - Terraform state가 있는 경우 사용

2. **AWS CLI로 조회** (fallback)
   - Terraform output이 없거나 실패한 경우
   - AWS 리소스를 직접 조회

3. **실패 시 에러** (필수 값인 경우)
   - 필수 값(예: EC2_PUBLIC_IP)이 없으면 워크플로우 실패

### 자동 조회되는 값 상세

#### EC2_PUBLIC_IP

- **1차 시도**: `terraform output -raw ec2_public_ip`
- **2차 시도**: `aws ec2 describe-instances --filters "Name=tag:Name,Values=authcore-k8s-node-prod"`

#### API_GATEWAY_ID

- **1차 시도**: `terraform output -raw api_gateway_id`
- **2차 시도**: `aws apigatewayv2 get-apis --query "Items[?contains(Name, 'authcore')].ApiId"`

#### JWT_SECRET

- **자동 처리**: `deploy_to_k8s.py` 스크립트가 Secrets Manager에서 자동으로 가져옴
- **Secrets Manager 이름**: `authcore/jwt-secret-prod`

#### SECRETS_MANAGER_ARN

- **1차 시도**: `terraform output -raw secrets_manager_arn`
- **2차 시도**: `aws secretsmanager describe-secret --secret-id "authcore/jwt-secret-prod"`

---

## 🔧 Secrets 설정 방법

### 1. AWS 자격 증명

```bash
# AWS IAM 콘솔에서 사용자 생성
# 필요한 권한:
# - ECR: 이미지 푸시/풀
# - EC2: 인스턴스 조회
# - Secrets Manager: JWT_SECRET 읽기
# - API Gateway: 백엔드 업데이트
```

**GitHub Secrets에 등록:**

- `AWS_ACCESS_KEY_ID`: IAM 사용자의 Access Key ID
- `AWS_SECRET_ACCESS_KEY`: IAM 사용자의 Secret Access Key

### 2. SSH 개인 키

```bash
# EC2 인스턴스 접근용 SSH 키
# Terraform으로 생성한 키 페어의 개인 키 내용 전체를 복사
cat ~/.ssh/authcore-k8s-key.pem
```

**GitHub Secrets에 등록:**

- `SSH_PRIVATE_KEY`: SSH 개인 키 파일 내용 전체 (-----BEGIN 부터 -----END 까지)

### 3. 빠른 설정 체크리스트

- [ ] `AWS_ACCESS_KEY_ID` 등록
- [ ] `AWS_SECRET_ACCESS_KEY` 등록
- [ ] `SSH_PRIVATE_KEY` 등록

**완료!** 나머지 값들은 워크플로우가 자동으로 조회합니다.

---

## 📊 워크플로우 Job 상세

### test Job

**실행 조건**: 모든 브랜치/PR

**단계:**

1. 코드 체크아웃
2. Node.js 23.10.0 설정
3. 의존성 설치 (`npm ci`)
4. Unit 테스트 실행
5. Integration 테스트 실행
6. 커버리지 리포트 생성
7. Codecov 업로드 (선택사항)

**소요 시간**: 약 2-3분

### build-and-push Job

**실행 조건**: `main` 브랜치에 push, `test` job 성공 후

**단계:**

1. 코드 체크아웃
2. Python 3.11 설정
3. 의존성 설치
4. AWS 자격 증명 설정
5. ECR 리포지토리 URI 조회
6. Podman 설치
7. ECR 로그인 (Podman)
8. 이미지 빌드 및 푸시 (Podman)
9. 이미지 URI 파일 업로드 (artifact)

**소요 시간**: 약 3-5분

### deploy Job

**실행 조건**: `main` 브랜치에 push, `build-and-push` job 성공 후

**단계:**

1. 코드 체크아웃
2. 이미지 URI artifact 다운로드
3. Python 3.11 설정
4. 의존성 설치
5. AWS 자격 증명 설정
6. 인프라 값 자동 조회:
   - EC2 Public IP
   - API Gateway ID
   - Secrets Manager ARN
7. ECR 리포지토리 URI 조회
8. kubectl 설치
9. SSH 키 설정
10. kubeconfig 설정
11. Kubernetes 배포 (k3s)
12. API Gateway 백엔드 업데이트 (변경된 경우에만)
13. 배포 검증

**소요 시간**: 약 5-7분

#### API Gateway 백엔드 업데이트 최적화

**개선 사항**: 백엔드 URL이 변경된 경우에만 업데이트합니다.

- **기존 동작**: Integration이 있으면 무조건 업데이트 (불필요한 API 호출)
- **개선된 동작**:
  1. 기존 Integration의 백엔드 URL 확인
  2. 새 백엔드 URL과 비교
  3. 동일하면 업데이트 건너뜀
  4. 변경된 경우에만 업데이트

**장점**:

- 불필요한 API 호출 제거
- 워크플로우 실행 시간 단축
- API Gateway 변경 이력 최소화

## ⚠️ 보안 주의사항

1. **절대 공개하지 마세요**: Secrets는 절대 코드나 문서에 하드코딩하지 마세요
2. **최소 권한 원칙**: IAM 사용자에게 필요한 최소한의 권한만 부여하세요
3. **정기적 로테이션**: Secrets는 정기적으로 변경하는 것을 권장합니다
4. **GitHub Secrets 사용**: 환경 변수 대신 Secrets를 사용하여 민감한 정보를 보호하세요

---

## 🔍 문제 해결

### 워크플로우가 실패하는 경우

1. **Secrets 확인**
   - GitHub 저장소 → Settings → Secrets and variables → Actions
   - 필수 Secrets 3개가 모두 등록되어 있는지 확인

2. **AWS 권한 확인**
   - IAM 사용자에게 필요한 권한이 있는지 확인
   - ECR, EC2, Secrets Manager, API Gateway 접근 권한 필요

3. **Terraform 상태 확인**
   - Terraform이 정상적으로 적용되었는지 확인
   - `terraform output` 명령어로 출력값 확인

4. **워크플로우 로그 확인**
   - GitHub Actions 탭에서 워크플로우 실행 로그 확인
   - 실패한 단계의 로그를 자세히 확인

### 일반적인 문제

#### "EC2 instance not found"

- **원인**: EC2 인스턴스가 실행 중이 아니거나 태그가 잘못됨
- **해결**: AWS 콘솔에서 인스턴스 상태 확인, 태그 확인

#### "ECR repository not found"

- **원인**: ECR 리포지토리가 생성되지 않음
- **해결**: Terraform으로 ECR 리포지토리 생성

#### "API Gateway ID not found"

- **원인**: API Gateway가 없거나 이름이 다름
- **해결**: AWS 콘솔에서 API Gateway 확인, Terraform output 확인

#### "JWT secret not found"

- **원인**: Secrets Manager에 시크릿이 없음
- **해결**: Terraform으로 Secrets Manager 시크릿 생성

---

## 📚 관련 문서

- [GitHub Actions Secrets 문서](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [AWS IAM 사용자 생성 가이드](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html)
- [SSH 키 생성 가이드](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
- [k3s 공식 문서](https://k3s.io/)
- [Podman 공식 문서](https://podman.io/)

---

## 🎉 요약

- **필수 Secrets**: 3개만 등록하면 됨
- **자동 조회**: 4개 값 자동 조회
- **워크플로우**: test → build → deploy 순차 실행
- **비용 최적화**: 최소 비용으로 컨테이너 오케스트레이션 실습 가능
