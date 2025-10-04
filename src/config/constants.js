// AuthCore 상수 정의

// 사용자 검증 규칙
const USER_VALIDATION = {
  USERNAME: {
    MIN_LENGTH: 3,
    MAX_LENGTH: 20,
    PATTERN: /^[a-zA-Z0-9_]+$/
  },
  PASSWORD: {
    MIN_LENGTH: 4
  }
};

// JWT 설정
const JWT_CONFIG = {
  ACCESS_EXPIRES_IN: "15m",
  REFRESH_EXPIRES_IN: "7d"
};

// DynamoDB 테이블명
const TABLES = {
  USERS: "AuthCore_Users",
  REFRESH_TOKENS: "AuthCore_RefreshTokens"
};

// HTTP 상태 코드
const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500
};

// 에러 메시지
const ERROR_MESSAGES = {
  USERNAME_LENGTH: "닉네임은 3-20자 사이여야 합니다.",
  PASSWORD_LENGTH: "비밀번호는 4자 이상이어야 합니다.",
  USERNAME_DUPLICATE: "이미 사용 중인 닉네임입니다.",
  USER_NOT_FOUND: "사용자를 찾을 수 없습니다.",
  USER_INACTIVE: "비활성화된 계정입니다.",
  PASSWORD_MISMATCH: "비밀번호가 일치하지 않습니다.",
  INVALID_TOKEN: "유효하지 않은 토큰입니다.",
  TOKEN_EXPIRED: "토큰이 만료되었습니다.",
  RATE_LIMIT_EXCEEDED: "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
};

// 성공 메시지
const SUCCESS_MESSAGES = {
  REGISTRATION: "회원가입이 완료되었습니다.",
  LOGIN: "로그인이 완료되었습니다.",
  LOGOUT: "로그아웃되었습니다.",
  USERNAME_UPDATED: "닉네임이 변경되었습니다.",
  PASSWORD_UPDATED: "비밀번호가 성공적으로 변경되었습니다.",
  TOKEN_REFRESHED: "토큰이 갱신되었습니다."
};

module.exports = {
  USER_VALIDATION,
  JWT_CONFIG,
  TABLES,
  HTTP_STATUS,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES
};
