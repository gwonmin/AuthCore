# 🚀 AuthCore 배포 가이드

AuthCore를 AWS에 배포하는 방법을 안내합니다.

## 📋 **사전 준비사항**

### 1. AWS 계정 및 자격 증명 설정

```bash
# AWS CLI 설치 (이미 설치되어 있다면 생략)
# Windows: https://aws.amazon.com/cli/
# macOS: brew install awscli
# Linux: sudo apt-get install awscli

# AWS 자격 증명 설정
aws configure
```

다음 정보를 입력하세요:
- **AWS Access Key ID**: IAM 사용자의 Access Key
- **AWS Secret Access Key**: IAM 사용자의 Secret Key
- **Default region name**: `ap-northeast-2` (서울)
- **Default output format**: `json`

### 2. IAM 권한 설정

다음 권한이 필요합니다:
- `dynamodb:*` (DynamoDB 테이블 생성/관리)
- `lambda:*` (Lambda 함수 생성/관리)
- `apigateway:*` (API Gateway 생성/관리)
- `iam:*` (역할 생성/관리)
- `cloudformation:*` (CloudFormation 스택 관리)

### 3. Serverless Framework 설치

```bash
# Serverless Framework 전역 설치
npm install -g serverless

# 또는 npx 사용 (권장)
npx serverless --version
```

## 🔧 **환경 설정**

### 1. 환경 변수 파일 생성

```bash
# .env 파일 생성
cp env.example .env
```

### 2. 환경 변수 수정

`.env` 파일을 열어서 다음 값들을 수정하세요:

```env
# JWT 설정 (보안을 위해 강력한 비밀키 사용)
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# AWS 설정
AWS_REGION=ap-northeast-2

# 프로덕션 환경 설정
NODE_ENV=production
```

## 🗄️ **DynamoDB 테이블 생성**

### 1. 로컬에서 테이블 생성 (개발용)

```bash
# 로컬 DynamoDB 테이블 생성
npm run create-tables
```

### 2. AWS에서 테이블 생성 (프로덕션용)

```bash
# AWS 리전 설정
export AWS_REGION=ap-northeast-2

# 테이블 생성
node scripts/create-tables.js
```

## 🚀 **배포 실행**

### 1. 프로덕션 환경 배포

```bash
# 프로덕션 환경에 배포
npm run deploy
```

## 📊 **배포 확인**

### 1. 배포 상태 확인

```bash
# 배포 로그 확인
npm run logs

# 또는
serverless logs -f api --tail
```

### 2. API 엔드포인트 확인

배포 완료 후 출력되는 URL을 확인하세요:
```
endpoints:
  ANY - https://your-api-id.execute-api.ap-northeast-2.amazonaws.com/prod/{proxy+}
```

### 3. API 테스트

```bash
# 회원가입 테스트
curl -X POST https://your-api-id.execute-api.ap-northeast-2.amazonaws.com/prod/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

## 🔧 **환경 설정**

### 프로덕션 환경 (prod)

```yaml
# serverless.yml에서 stage: prod
provider:
  stage: prod
  region: ap-northeast-2
```

## 🛠️ **배포 후 관리**

### 1. 로그 확인

```bash
# 실시간 로그 확인
npm run logs

# 특정 시간대 로그 확인
serverless logs -f api --startTime 2024-01-01T00:00:00
```

### 2. 함수 업데이트

```bash
# 코드 변경 후 재배포
npm run deploy

# 특정 함수만 업데이트
serverless deploy function -f api
```

### 3. 환경 변수 업데이트

```bash
# 환경 변수 설정
serverless config credentials --provider aws --key YOUR_KEY --secret YOUR_SECRET

# 환경 변수 확인
serverless print
```

## 🗑️ **배포 제거**

```bash
# 전체 스택 제거
npm run remove

# 또는
serverless remove
```

## 🔍 **문제 해결**

### 1. 권한 오류

```bash
# AWS 자격 증명 확인
aws sts get-caller-identity

# IAM 정책 확인
aws iam list-attached-user-policies --user-name YOUR_USERNAME
```

### 2. DynamoDB 테이블 오류

```bash
# 테이블 존재 확인
aws dynamodb list-tables --region ap-northeast-2

# 테이블 상태 확인
aws dynamodb describe-table --table-name AuthCore_Users --region ap-northeast-2
```

### 3. Lambda 함수 오류

```bash
# 함수 로그 확인
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/authcore

# 함수 상태 확인
aws lambda get-function --function-name authcore-prod-api
```

## 📝 **배포 체크리스트**

- [ ] AWS 자격 증명 설정 완료
- [ ] IAM 권한 확인 완료
- [ ] Serverless Framework 설치 완료
- [ ] 환경 변수 설정 완료
- [ ] DynamoDB 테이블 생성 완료
- [ ] 배포 실행 완료
- [ ] API 엔드포인트 테스트 완료
- [ ] 로그 확인 완료

## 🆘 **지원**

문제가 발생하면 다음을 확인하세요:

1. **AWS 콘솔**에서 리소스 상태 확인
2. **CloudFormation 스택** 상태 확인
3. **Lambda 함수 로그** 확인
4. **API Gateway 로그** 확인

---

**AuthCore 배포 완료!** 🎉

이제 여러 플랫폼에서 AuthCore API를 사용할 수 있습니다!
