const { HTTP_STATUS, ERROR_MESSAGES } = require('../config/constants');

/**
 * 공통 에러 처리 미들웨어
 * @param {Error} error - 에러 객체
 * @param {Object} request - Fastify request 객체
 * @param {Object} reply - Fastify reply 객체
 */
function errorHandler(error, request, reply) {
  // 로깅
  console.error('Error occurred:', {
    message: error.message,
    stack: error.stack,
    url: request.url,
    method: request.method,
    timestamp: new Date().toISOString()
  });

  // JWT 관련 에러
  if (error.message.includes('jwt') || error.message.includes('token')) {
    return reply.status(HTTP_STATUS.UNAUTHORIZED).send({
      success: false,
      message: ERROR_MESSAGES.INVALID_TOKEN,
      statusCode: HTTP_STATUS.UNAUTHORIZED
    });
  }

  // 유효성 검사 에러
  if (error.message.includes('닉네임') || error.message.includes('비밀번호')) {
    return reply.status(HTTP_STATUS.BAD_REQUEST).send({
      success: false,
      message: error.message,
      statusCode: HTTP_STATUS.BAD_REQUEST
    });
  }

  // 사용자 관련 에러
  if (error.message.includes('사용자') || error.message.includes('계정')) {
    return reply.status(HTTP_STATUS.BAD_REQUEST).send({
      success: false,
      message: error.message,
      statusCode: HTTP_STATUS.BAD_REQUEST
    });
  }

  // 기본 서버 에러
  return reply.status(HTTP_STATUS.INTERNAL_SERVER_ERROR).send({
    success: false,
    message: '서버 내부 오류가 발생했습니다.',
    statusCode: HTTP_STATUS.INTERNAL_SERVER_ERROR
  });
}

/**
 * 404 에러 처리
 * @param {Object} request - Fastify request 객체
 * @param {Object} reply - Fastify reply 객체
 */
function notFoundHandler(request, reply) {
  return reply.status(HTTP_STATUS.NOT_FOUND).send({
    success: false,
    message: '요청한 리소스를 찾을 수 없습니다.',
    statusCode: HTTP_STATUS.NOT_FOUND
  });
}

module.exports = {
  errorHandler,
  notFoundHandler
};
