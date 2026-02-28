# 🔐 AuthCore API 문서

AuthCore는 여러 플랫폼에 연동 가능한 인증 서비스를 제공하는 서버리스 API입니다.

## 📋 기본 정보

- **Base URL**: `https://your-api-gateway-url.amazonaws.com/prod`
- **Content-Type**: `application/json`
- **인증 방식**: JWT Bearer Token

---

## 🚀 시작하기

### 환경 설정

1. 환경 변수 설정:
```bash
cp env.example .env
```

2. 필요한 환경 변수:
```env
JWT_SECRET=your-super-secret-jwt-key
AWS_REGION=ap-northeast-2
NODE_ENV=production
```

---

## 🔑 인증 API

### 1. 회원가입

**POST** `/auth/register`

새로운 사용자 계정을 생성합니다.

#### 요청

```json
{
  "username": "testuser",
  "password": "testpass123"
}
```

#### 응답 (성공 - 201)

```json
{
  "success": true,
  "data": {
    "user": {
      "user_id": "uuid-here",
      "username": "testuser",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00.000Z"
    },
    "tokens": {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
}
```

#### 응답 (실패 - 400)

```json
{
  "success": false,
  "message": "이미 사용 중인 닉네임입니다."
}
```

---

### 2. 로그인

**POST** `/auth/login`

사용자 인증을 수행합니다.

#### 요청

```json
{
  "username": "testuser",
  "password": "testpass123"
}
```

#### 응답 (성공 - 200)

```json
{
  "success": true,
  "data": {
    "user": {
      "user_id": "uuid-here",
      "username": "testuser",
      "is_active": true,
      "last_login_at": "2024-01-01T00:00:00.000Z"
    },
    "tokens": {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
}
```

---

### 3. 현재 사용자 정보 조회

**GET** `/auth/me`

현재 로그인한 사용자의 정보를 조회합니다.

#### 요청 헤더

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

#### 응답 (성공 - 200)

```json
{
  "success": true,
  "data": {
    "user_id": "uuid-here",
    "username": "testuser",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00.000Z",
    "last_login_at": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### 4. 토큰 갱신

**POST** `/auth/refresh`

만료된 Access Token을 갱신합니다.

#### 요청

```json
{
  "refreshToken": "YOUR_REFRESH_TOKEN"
}
```

#### 응답 (성공 - 200)

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

---

### 5. 닉네임 변경

**PUT** `/auth/username`

사용자의 닉네임을 변경합니다.

#### 요청 헤더

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

#### 요청

```json
{
  "newUsername": "newusername",
  "password": "testpass123"
}
```

#### 응답 (성공 - 200)

```json
{
  "success": true,
  "data": {
    "user_id": "uuid-here",
    "username": "newusername",
    "is_active": true,
    "username_changed_at": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### 6. 비밀번호 변경

**PUT** `/auth/password`

사용자의 비밀번호를 변경합니다.

#### 요청 헤더

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

#### 요청

```json
{
  "currentPassword": "testpass123",
  "newPassword": "newpass123"
}
```

#### 응답 (성공 - 200)

```json
{
  "success": true,
  "message": "비밀번호가 성공적으로 변경되었습니다."
}
```

---

### 7. 로그아웃

**POST** `/auth/logout`

사용자를 로그아웃하고 모든 토큰을 무효화합니다.

#### 요청 헤더

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

#### 요청

```json
{
  "refreshToken": "YOUR_REFRESH_TOKEN"
}
```

#### 응답 (성공 - 200)

```json
{
  "success": true,
  "message": "로그아웃되었습니다."
}
```

---

## 🔒 보안 기능

### Rate Limiting
- **제한**: 분당 100회 요청
- **초과 시**: 429 상태 코드 반환

### CORS 설정
- **허용된 Origin**: 모든 도메인 (`*`)
- **허용된 메서드**: GET, POST, PUT, DELETE, OPTIONS
- **허용된 헤더**: Content-Type, Authorization 등

### 토큰 보안
- **Access Token**: 15분 만료
- **Refresh Token**: 7일 만료, 데이터베이스에 해시 저장
- **토큰 무효화**: 로그아웃 시 모든 토큰 무효화

---

## 📊 에러 코드

| 상태 코드 | 설명 | 예시 |
|---------|------|------|
| 200 | 성공 | 요청이 성공적으로 처리됨 |
| 201 | 생성 성공 | 사용자 계정이 성공적으로 생성됨 |
| 400 | 잘못된 요청 | 입력값이 유효하지 않음 |
| 401 | 인증 실패 | 토큰이 유효하지 않거나 만료됨 |
| 404 | 리소스 없음 | 사용자를 찾을 수 없음 |
| 429 | 요청 한도 초과 | Rate limit 초과 |
| 500 | 서버 오류 | 내부 서버 오류 |

---

## 🧪 테스트

### 로컬 개발 환경 실행

```bash
# 의존성 설치
npm install

# 환경 변수 설정
cp env.example .env

# 로컬 서버 실행 (테스트용)
IS_LOCAL=true node src/index.js
```

### 테스트 실행

```bash
# 전체 테스트
npm test

# 단위 테스트만
npm run test:unit

# 통합 테스트만
npm run test:integration

# 커버리지 포함 테스트
npm run test:coverage
```

### API 테스트 예제

```bash
# 회원가입
curl -X POST http://localhost:4000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# 로그인
curl -X POST http://localhost:4000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

---

## 🚀 배포

배포는 GitHub Actions CI/CD 파이프라인이 자동 수행하거나, 수동으로 진행할 수 있습니다.
자세한 내용은 [배포 가이드](./DEPLOYMENT_GUIDE.md)를 참고하세요.
