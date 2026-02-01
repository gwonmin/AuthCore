# GitHub Actions CI/CD 워크플로우 가이드

## 📋 개요

이 문서는 AuthCore 프로젝트의 GitHub Actions CI/CD 워크플로우에 대한 종합 가이드입니다.

### 워크플로우 구조 (인프라 + 앱 모두 CI 이력 관리)

```
ci-cd.yml
├── test job (모든 브랜치/PR)
│   ├── Node.js 23.10.0에서 테스트 실행
│   ├── Unit / Integration 테스트
│   └── 커버리지 리포트
│
├── terraform-plan job (PR 시, TF_STATE_BUCKET 있을 때만)
│   ├── Terraform init (S3 backend)
│   └── terraform plan → 무엇이 생성/수정/삭제되는지 미리보기
│
├── terraform-apply job (main push 시)
│   ├── Terraform init (S3 backend)
│   └── terraform apply -auto-approve → 인프라 반영 (추가 AWS 서비스, 보안 조치 등 전부 이력 관리)
│
├── build-and-push job (needs: test, terraform-apply / main만)
│   ├── Podman으로 이미지 빌드
│   └── ECR에 이미지 푸시
│
└── deploy job (needs: build-and-push, main만)
    ├── kubeconfig 설정
    ├── Kubernetes 배포 (k3s)
    ├── API Gateway 백엔드 업데이트
    └── 배포 검증
```

---

## 🔐 GitHub Secrets 설정

### 필수 Secrets (4개, main에서 Terraform apply 사용 시)

GitHub 저장소의 **Settings → Secrets and variables → Actions**에서 다음 Secrets를 등록해야 합니다:

| Secret 이름             | 설명                            | 예시                                       | 필수 여부 |
| ----------------------- | ------------------------------- | ------------------------------------------ | --------- |
| `AWS_ACCESS_KEY_ID`     | AWS 액세스 키 ID                | `AKIAIOSFODNN7EXAMPLE`                     | ✅ 필수   |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 액세스 키            | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | ✅ 필수   |
| `SSH_PRIVATE_KEY`       | EC2 인스턴스 접근용 SSH 개인 키 | `-----BEGIN RSA PRIVATE KEY-----...`       | ✅ 필수   |
| `TF_STATE_BUCKET`       | Terraform state S3 버킷 이름    | `TERRAFORM_STATE_BUCKET` (버킷 이름만)   | ✅ 필수*  |

\* **TF_STATE_BUCKET**: main 브랜치 push 시 `terraform apply`가 CI에서 실행되므로 **필수**입니다. PR에서 `terraform plan`을 보려면 역시 필요합니다. 아래 "Terraform S3 백엔드"에서 버킷 생성 후 등록하세요.

### 자동 조회되는 값들 (Secrets 불필요)

인프라는 **로컬에서 Terraform으로 한 번 세팅**한 뒤, CI는 **이미지 빌드 + k8s 배포**만 담당합니다.  
필요한 값(EC2 IP, API Gateway ID 등)은 CI에서 **AWS CLI로 현재 리소스를 조회**합니다:

| 값 이름               | 자동 조회 방법   | 워크플로우 단계              | 설명                                                     |
| --------------------- | ---------------- | ---------------------------- | -------------------------------------------------------- |
| `EC2_PUBLIC_IP`       | AWS CLI          | `Get infrastructure values`  | EC2 인스턴스 Public IP 조회                              |
| `API_GATEWAY_ID`      | AWS CLI          | `Get infrastructure values`  | API Gateway ID 조회 (authcore 이름 패턴)                 |
| `JWT_SECRET`          | Secrets Manager  | `Deploy to Kubernetes (k3s)` | `deploy_to_k8s.py`가 Secrets Manager에서 가져옴           |
| `SECRETS_MANAGER_ARN` | AWS CLI          | `Get infrastructure values`  | Secrets Manager ARN 조회                                 |

**🎉 개선 사항**: **필수 Secrets 4개** (TF_STATE_BUCKET 포함) 등록 시 plan/apply·빌드·배포 모두 CI에서 동작합니다.

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
  ↓ (성공 시)
terraform-plan job (TF_STATE_BUCKET 있으면)
  └── terraform plan → 인프라 변경 미리보기 (생성/수정/삭제 가시화)
```

- **실행되는 job**: `test`, (선택) `terraform-plan`
- **목적**: 코드·인프라 변경 검증. plan으로 "이 PR 머지하면 인프라에 뭐가 바뀌는지" 확인 가능

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
terraform-apply job  ← 인프라 반영 (추가 AWS 서비스, 보안 조치 등 전부 코드·이력 관리)
  ↓ (성공 시)
build-and-push job
  ↓ (성공 시)
deploy job
```

- **실행되는 job**: `test` → `terraform-apply` → `build-and-push` → `deploy`
- **목적**: 인프라 적용 후 앱 이미지 빌드·배포. **인프라 변경도 Git + CI 이력으로 남음**
- **조건**: TF_STATE_BUCKET 필수 (없으면 apply 단계에서 실패)

---

## 🏗️ Terraform S3 백엔드 (인프라 이력 관리)

main push 시 **terraform apply**가 CI에서 실행되려면 **state를 S3에 두고** GitHub Secrets에 **TF_STATE_BUCKET**을 등록해야 합니다.  
이렇게 하면 **인프라 추가·보안 조치 등 모든 변경이 Git + CI 이력**으로 남습니다.

### 1. S3 버킷 생성 (한 번만)

```bash
aws s3 mb s3://YOUR_TERRAFORM_STATE_BUCKET --region ap-northeast-2
aws s3api put-bucket-versioning --bucket YOUR_TERRAFORM_STATE_BUCKET \
  --versioning-configuration Status=Enabled
```

(버킷 이름 예: `authcore-terraform-state`)

### 2. GitHub Secrets에 등록

- **TF_STATE_BUCKET** = `YOUR_TERRAFORM_STATE_BUCKET` (버킷 이름만, `s3://` 제외)

### 3. 로컬에서 state를 S3로 이전 (기존 로컬 state가 있다면)

```bash
cd terraform
terraform init -reconfigure \
  -backend-config="bucket=YOUR_TERRAFORM_STATE_BUCKET" \
  -backend-config="key=authcore/prod/terraform.tfstate" \
  -backend-config="region=ap-northeast-2"
# 마이그레이션 프롬프트에서 yes 입력 시 로컬 state가 S3로 복사됨
terraform plan  # 확인 후 필요 시 apply
```

bucket/key/region은 위 명령줄 또는 `-backend-config=backend.hcl` 형태의 파일로 전달하면 됩니다.

---

## 🔄 자동 조회 로직 (deploy job)

**배포(deploy)** 단계에서는 여전히 **AWS CLI**로 EC2 IP, API Gateway ID 등을 조회합니다.  
(인프라 반영은 `terraform-apply` job에서 하고, deploy는 그 위에서 앱만 배포)

### CI에서의 조회

- **EC2_PUBLIC_IP**: `aws ec2 describe-instances` (필수. 없으면 배포 실패)
- **API_GATEWAY_ID**: `aws apigatewayv2 get-apis` (없으면 "Update API Gateway backend" 단계만 스킵)
- **SECRETS_MANAGER_ARN**: `aws secretsmanager describe-secret` (없으면 JWT_SECRET은 기본값 등 사용)

### 자동 조회되는 값 상세

#### EC2_PUBLIC_IP

- **CI**: `aws ec2 describe-instances --filters "Name=tag:Name,Values=authcore-k8s-node-prod"` (필수)

#### API_GATEWAY_ID

- **CI**: `aws apigatewayv2 get-apis --query "Items[?contains(Name, 'authcore')].ApiId"`  
- **없을 때**: "Update API Gateway backend" 단계 스킵 (배포 자체는 성공)

#### JWT_SECRET

- **자동 처리**: `deploy_to_k8s.py` 스크립트가 Secrets Manager에서 자동으로 가져옴
- **Secrets Manager 이름**: `authcore/jwt-secret-prod`

#### SECRETS_MANAGER_ARN

- **CI**: `aws secretsmanager describe-secret --secret-id "authcore/jwt-secret-prod"` (선택)

---

## 🔧 Secrets 설정 방법

### 1. AWS 자격 증명

```bash
# AWS IAM 콘솔에서 사용자 생성
# 필요한 권한:
# - ECR: 이미지 푸시/풀
# - EC2: 인스턴스 조회·생성·수정 (Terraform apply 시)
# - Secrets Manager: JWT_SECRET 읽기
# - API Gateway: 백엔드 업데이트
# - S3: Terraform state 버킷 읽기/쓰기 (TF_STATE_BUCKET)
# - 기타 Terraform이 관리하는 리소스 (DynamoDB, VPC, IAM 등)
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
- [ ] S3 버킷 생성 후 `TF_STATE_BUCKET` 등록 (main에서 terraform apply 사용 시 필수)

**완료!** PR에서 `terraform plan`, main push에서 `terraform apply` → 인프라 변경 전부 이력 관리됩니다.

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

**소요 시간**: 약 3-5분

### deploy Job

**실행 조건**: `main` 브랜치에 push, `build-and-push` job 성공 후

**단계:**

1. 코드 체크아웃
2. Python 3.11 설정
3. 의존성 설치
4. AWS 자격 증명 설정
5. 인프라 값 자동 조회:
   - EC2 Public IP
   - API Gateway ID
   - Secrets Manager ARN
6. ECR 리포지토리 URI 조회
7. kubectl 설치
8. SSH 키 설정
9. kubeconfig 설정
10. Kubernetes 배포 (k3s) — `IMAGE_URI`는 `ECR_REPOSITORY_URI:github.sha`로 전달
11. API Gateway 백엔드 업데이트 (API_GATEWAY_ID가 있을 때만, 변경된 경우에만)
12. 배포 검증

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

#### API Gateway 백엔드 업데이트 조건부 실행

- **API_GATEWAY_ID가 없을 때**: "Update API Gateway backend" 단계는 **스킵**됩니다. 배포(K8s)는 그대로 진행됩니다.
- **API_GATEWAY_ID가 있을 때만**: API Gateway Integration 업데이트가 실행됩니다.

---

## 🔧 워크플로우 설계 (인프라 + 앱 이력 관리)

- **인프라**: Terraform 코드로 관리. **PR 시 plan**, **main push 시 apply** → 추가 AWS 서비스, 보안 조치 등 **전부 Git·CI 이력**으로 남음.
- **CI 역할**: `terraform-apply` 후 이미지 빌드 + k8s 배포. 배포 시 필요한 값(EC2 IP, API Gateway ID 등)은 **AWS CLI**로 조회.
- **선택적 단계**: API_GATEWAY_ID가 없으면 "Update API Gateway backend" 단계만 스킵 (`if: steps.infra_values.outputs.API_GATEWAY_ID != ''`).

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
   - 필수 Secrets 4개(AWS 2개, SSH_PRIVATE_KEY, TF_STATE_BUCKET)가 모두 등록되어 있는지 확인

2. **AWS 권한 확인**
   - IAM 사용자에게 필요한 권한이 있는지 확인
   - ECR, EC2, Secrets Manager, API Gateway 접근 권한 필요

3. **인프라 확인**
   - 로컬에서 Terraform 적용이 완료되었는지 확인 (EC2, ECR, API Gateway 등)
   - AWS 콘솔에서 리소스 존재 여부 확인

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

#### "API Gateway ID not found" / API Gateway 단계 스킵

- **원인**: API Gateway가 없거나 이름이 authcore/AuthCore를 포함하지 않음
- **동작**: "Update API Gateway backend" 단계는 **스킵**되고, K8s 배포는 정상 완료됨
- **해결**: API Gateway가 필요하면 AWS 콘솔에서 생성 후 이름에 `authcore` 포함, 또는 Terraform 적용

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

- **필수 Secrets**: 4개(AWS 2개, SSH_PRIVATE_KEY, TF_STATE_BUCKET) 등록
- **자동 조회**: 4개 값 자동 조회
- **워크플로우**: test → build → deploy 순차 실행
- **비용 최적화**: 최소 비용으로 컨테이너 오케스트레이션 실습 가능
