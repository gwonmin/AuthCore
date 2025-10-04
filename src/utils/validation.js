const { USER_VALIDATION, ERROR_MESSAGES } = require('../config/constants');

/**
 * 사용자명 유효성 검사
 * @param {string} username - 검사할 사용자명
 * @returns {Object} { isValid: boolean, error?: string }
 */
function validateUsername(username) {
  if (!username) {
    return { isValid: false, error: ERROR_MESSAGES.USERNAME_LENGTH };
  }

  if (username.length < USER_VALIDATION.USERNAME.MIN_LENGTH || 
      username.length > USER_VALIDATION.USERNAME.MAX_LENGTH) {
    return { isValid: false, error: ERROR_MESSAGES.USERNAME_LENGTH };
  }

  if (!USER_VALIDATION.USERNAME.PATTERN.test(username)) {
    return { isValid: false, error: "닉네임은 영문, 숫자, 언더스코어만 사용할 수 있습니다." };
  }

  return { isValid: true };
}

/**
 * 비밀번호 유효성 검사
 * @param {string} password - 검사할 비밀번호
 * @returns {Object} { isValid: boolean, error?: string }
 */
function validatePassword(password) {
  if (!password) {
    return { isValid: false, error: ERROR_MESSAGES.PASSWORD_LENGTH };
  }

  if (password.length < USER_VALIDATION.PASSWORD.MIN_LENGTH) {
    return { isValid: false, error: ERROR_MESSAGES.PASSWORD_LENGTH };
  }

  return { isValid: true };
}

/**
 * 사용자 데이터에서 비밀번호 해시 제거
 * @param {Object} user - 사용자 데이터
 * @returns {Object} 비밀번호 해시가 제거된 사용자 데이터
 */
function sanitizeUser(user) {
  if (!user) return null;
  
  const { password_hash, ...sanitizedUser } = user;
  return sanitizedUser;
}

/**
 * 에러 응답 생성
 * @param {string} message - 에러 메시지
 * @param {number} statusCode - HTTP 상태 코드
 * @returns {Object} 에러 응답 객체
 */
function createErrorResponse(message, statusCode = 400) {
  return {
    success: false,
    message,
    statusCode
  };
}

/**
 * 성공 응답 생성
 * @param {*} data - 응답 데이터
 * @param {string} message - 성공 메시지
 * @param {number} statusCode - HTTP 상태 코드
 * @returns {Object} 성공 응답 객체
 */
function createSuccessResponse(data = null, message = null, statusCode = 200) {
  const response = {
    success: true,
    statusCode
  };

  if (data !== null) {
    response.data = data;
  }

  if (message) {
    response.message = message;
  }

  return response;
}

module.exports = {
  validateUsername,
  validatePassword,
  sanitizeUser,
  createErrorResponse,
  createSuccessResponse
};
