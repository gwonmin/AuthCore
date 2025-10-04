# AuthCore API 테스트 명세

## 기본 정보
- **Base URL**: `http://localhost:4000`
- **Content-Type**: `application/json`

---

## 1. 회원가입 (POST /auth/register)

### 요청
```bash
curl -X POST http://localhost:4000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

### 응답 (성공)
```json
{
  "success": true,
  "data": {
    "user": {
      "user_id": "uuid-here",
      "username": "testuser",
      "level": 1,
      "total_quizzes": 0,
      "created_at": "2024-01-01T00:00:00.000Z"
    },
    "tokens": {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
}
```

### 응답 (실패)
```json
{
  "success": false,
  "message": "이미 사용 중인 닉네임입니다."
}
```

---

## 2. 로그인 (POST /auth/login)

### 요청
```bash
curl -X POST http://localhost:4000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

### 응답 (성공)
```json
{
  "success": true,
  "data": {
    "user": {
      "user_id": "uuid-here",
      "username": "testuser",
      "level": 1,
      "total_quizzes": 0,
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

## 3. 현재 사용자 정보 (GET /auth/me)

### 요청
```bash
curl -X GET http://localhost:4000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 응답 (성공)
```json
{
  "success": true,
  "data": {
    "user_id": "uuid-here",
    "username": "testuser",
    "level": 1,
    "total_quizzes": 0,
    "created_at": "2024-01-01T00:00:00.000Z",
    "last_login_at": "2024-01-01T00:00:00.000Z"
  }
}
```

---

## 4. 토큰 갱신 (POST /auth/refresh)

### 요청
```bash
curl -X POST http://localhost:4000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refreshToken": "YOUR_REFRESH_TOKEN"
  }'
```

### 응답 (성공)
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

## 5. 닉네임 변경 (PUT /auth/username)

### 요청
```bash
curl -X PUT http://localhost:4000/auth/username \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "newUsername": "newusername",
    "password": "testpass123"
  }'
```

### 응답 (성공)
```json
{
  "success": true,
  "data": {
    "user_id": "uuid-here",
    "username": "newusername",
    "level": 1,
    "total_quizzes": 0,
    "username_changed_at": "2024-01-01T00:00:00.000Z"
  }
}
```

---

## 6. 비밀번호 변경 (PUT /auth/password)

### 요청
```bash
curl -X PUT http://localhost:4000/auth/password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "currentPassword": "testpass123",
    "newPassword": "newpass123"
  }'
```

### 응답 (성공)
```json
{
  "success": true,
  "message": "비밀번호가 성공적으로 변경되었습니다."
}
```

---

## 7. 로그아웃 (POST /auth/logout)

### 요청
```bash
curl -X POST http://localhost:4000/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "refreshToken": "YOUR_REFRESH_TOKEN"
  }'
```

### 응답 (성공)
```json
{
  "success": true,
  "message": "로그아웃되었습니다."
}
```

---

## PowerShell 테스트 명령어

### 1. 회원가입
```powershell
Invoke-RestMethod -Uri "http://localhost:4000/auth/register" -Method POST -ContentType "application/json" -Body '{"username": "testuser", "password": "testpass123"}'
```

### 2. 로그인
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:4000/auth/login" -Method POST -ContentType "application/json" -Body '{"username": "testuser", "password": "testpass123"}'
$accessToken = $response.data.tokens.accessToken
```

### 3. 사용자 정보 조회
```powershell
Invoke-RestMethod -Uri "http://localhost:4000/auth/me" -Method GET -Headers @{"Authorization" = "Bearer $accessToken"}
```

---

## Postman Collection

### 환경 변수 설정
- `base_url`: `http://localhost:4000`
- `access_token`: (로그인 후 설정)
- `refresh_token`: (로그인 후 설정)

### 테스트 시나리오
1. 회원가입 → 토큰 저장
2. 로그인 → 토큰 갱신
3. 사용자 정보 조회
4. 닉네임 변경
5. 비밀번호 변경
6. 로그아웃

---

## 에러 코드

| 상태코드 | 설명 |
|---------|------|
| 200 | 성공 |
| 201 | 생성 성공 |
| 400 | 잘못된 요청 |
| 401 | 인증 실패 |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 429 | 요청 한도 초과 |
| 500 | 서버 오류 |
