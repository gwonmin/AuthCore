const { verifyAccessToken, getUserById, createDynamoDBClient } = require("../services/authService");

/**
 * JWT 토큰 인증 미들웨어
 * @param {Object} request - Fastify request 객체
 * @param {Object} reply - Fastify reply 객체
 * @returns {Promise<void>}
 */
async function authenticateToken(request, reply) {
  try {
    // Authorization 헤더에서 토큰 추출
    const authHeader = request.headers.authorization;
    
    if (!authHeader) {
      return reply.status(401).send({
        success: false,
        message: "Access token이 필요합니다.",
      });
    }

    // "Bearer " 접두사 제거
    const token = authHeader.replace("Bearer ", "");
    
    if (!token) {
      return reply.status(401).send({
        success: false,
        message: "유효하지 않은 토큰 형식입니다.",
      });
    }

    // 토큰 검증
    const decoded = verifyAccessToken(token);
    
    // 사용자 정보 조회
    const dynamoDBClient = createDynamoDBClient();
    const user = await getUserById(decoded.userId, dynamoDBClient);
    
    if (!user) {
      return reply.status(401).send({
        success: false,
        message: "사용자를 찾을 수 없습니다.",
      });
    }

    if (!user.is_active) {
      return reply.status(401).send({
        success: false,
        message: "비활성화된 계정입니다.",
      });
    }

    // request 객체에 사용자 정보 추가
    request.user = {
      userId: user.user_id,
      username: user.username,
      is_active: user.is_active,
    };

  } catch (error) {
    console.error("Authentication error:", error.message);
    
    return reply.status(401).send({
      success: false,
      message: "유효하지 않은 토큰입니다.",
    });
  }
}

/**
 * 선택적 인증 미들웨어 (토큰이 있으면 검증, 없으면 통과)
 * @param {Object} request - Fastify request 객체
 * @param {Object} reply - Fastify reply 객체
 * @returns {Promise<void>}
 */
async function optionalAuthenticate(request, reply) {
  try {
    const authHeader = request.headers.authorization;
    
    if (!authHeader) {
      // 토큰이 없으면 그냥 통과
      return;
    }

    const token = authHeader.replace("Bearer ", "");
    
    if (!token) {
      return;
    }

    // 토큰 검증 시도
    const decoded = verifyAccessToken(token);
    const user = await getUserById(decoded.userId);
    
    if (user && user.is_active) {
      request.user = {
        userId: user.user_id,
        username: user.username,
        is_active: user.is_active,
      };
    }
  } catch (error) {
    // 토큰 검증 실패해도 에러를 던지지 않고 그냥 통과
    console.log("Optional authentication failed:", error.message);
  }
}

/**
 * 관리자 권한 확인 미들웨어
 * @param {Object} request - Fastify request 객체
 * @param {Object} reply - Fastify reply 객체
 * @returns {Promise<void>}
 */
async function requireAdmin(request, reply) {
  // 먼저 일반 인증 확인
  await authenticateToken(request, reply);
  
  // 이미 에러 응답이 전송되었는지 확인
  if (reply.sent) {
    return;
  }

  // 관리자 권한 확인 (현재는 모든 활성 사용자 허용)
  if (!request.user || !request.user.is_active) {
    return reply.status(403).send({
      success: false,
      message: "활성화된 계정이 필요합니다.",
    });
  }
}

/**
 * 사용자 본인 확인 미들웨어 (URL 파라미터의 userId와 일치하는지 확인)
 * @param {Object} request - Fastify request 객체
 * @param {Object} reply - Fastify reply 객체
 * @returns {Promise<void>}
 */
async function requireOwnership(request, reply) {
  // 먼저 일반 인증 확인
  await authenticateToken(request, reply);
  
  // 이미 에러 응답이 전송되었는지 확인
  if (reply.sent) {
    return;
  }

  // URL 파라미터에서 userId 추출
  const targetUserId = request.params.userId || request.body.userId;
  
  if (!targetUserId) {
    return reply.status(400).send({
      success: false,
      message: "사용자 ID가 필요합니다.",
    });
  }

  // 본인 확인
  if (request.user.userId !== targetUserId) {
    return reply.status(403).send({
      success: false,
      message: "본인의 정보만 접근할 수 있습니다.",
    });
  }
}

module.exports = {
  authenticateToken,
  optionalAuthenticate,
  requireAdmin,
  requireOwnership,
};
