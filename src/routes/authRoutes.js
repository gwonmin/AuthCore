const {
  registerUser,
  loginUser,
  getUserById,
  updateUsername,
  updatePassword,
  generateTokenPair,
  verifyAndRefreshToken,
  revokeAllUserTokens,
} = require("../services/authService");
const { authenticateToken } = require("../middleware/authMiddleware");
const { HTTP_STATUS, ERROR_MESSAGES, SUCCESS_MESSAGES } = require("../config/constants");
const { createErrorResponse, createSuccessResponse } = require("../utils/validation");

/**
 * 인증 라우트 등록
 * @param {Object} fastify - Fastify 인스턴스
 * @param {Object} options - 옵션
 */
async function authRoutes(fastify, options) {
  // 회원가입
  fastify.post("/register", {
    schema: {
      body: {
        type: "object",
        required: ["username", "password"],
        properties: {
          username: {
            type: "string",
            minLength: 3,
            maxLength: 20,
            pattern: "^[a-zA-Z0-9_]+$",
          },
          password: {
            type: "string",
            minLength: 4,
          },
        },
      },
      response: {
        201: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            data: {
              type: "object",
              properties: {
                user: {
                  type: "object",
                  properties: {
                    user_id: { type: "string" },
                    username: { type: "string" },
                    is_active: { type: "boolean" },
                    created_at: { type: "string" },
                  },
                },
                tokens: {
                  type: "object",
                  properties: {
                    accessToken: { type: "string" },
                    refreshToken: { type: "string" },
                  },
                },
              },
            },
          },
        },
      },
    },
  }, async (request, reply) => {
    try {
      const { username, password } = request.body;

      // 사용자 등록
      const user = await registerUser(username, password);

      // 토큰 생성
      const tokens = await generateTokenPair(user.user_id, user.username);

      return reply.status(201).send({
        success: true,
        data: {
          user,
          tokens,
        },
      });
    } catch (error) {
      console.error("Registration error:", error.message);
      
      return reply.status(400).send({
        success: false,
        message: error.message,
      });
    }
  });

  // 로그인
  fastify.post("/login", {
    schema: {
      body: {
        type: "object",
        required: ["username", "password"],
        properties: {
          username: {
            type: "string",
            minLength: 3,
            maxLength: 20,
          },
          password: {
            type: "string",
            minLength: 4,
          },
        },
      },
      response: {
        200: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            data: {
              type: "object",
              properties: {
                user: {
                  type: "object",
                  properties: {
                    user_id: { type: "string" },
                    username: { type: "string" },
                    is_active: { type: "boolean" },
                    last_login_at: { type: "string" },
                  },
                },
                tokens: {
                  type: "object",
                  properties: {
                    accessToken: { type: "string" },
                    refreshToken: { type: "string" },
                  },
                },
              },
            },
          },
        },
      },
    },
  }, async (request, reply) => {
    try {
      const { username, password } = request.body;

      // 사용자 로그인
      const user = await loginUser(username, password);

      // 토큰 생성
      const tokens = await generateTokenPair(user.user_id, user.username);

      return reply.status(200).send({
        success: true,
        data: {
          user,
          tokens,
        },
      });
    } catch (error) {
      console.error("Login error:", error.message);
      
      return reply.status(401).send({
        success: false,
        message: error.message,
      });
    }
  });

  // 로그아웃
  fastify.post("/logout", {
    preHandler: [authenticateToken],
    schema: {
      body: {
        type: "object",
        required: ["refreshToken"],
        properties: {
          refreshToken: {
            type: "string",
          },
        },
      },
      response: {
        200: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            message: { type: "string" },
          },
        },
      },
    },
  }, async (request, reply) => {
    try {
      const { refreshToken } = request.body;
      const userId = request.user.userId;

      // 모든 refresh token 무효화
      await revokeAllUserTokens(userId);

      return reply.status(200).send({
        success: true,
        message: "로그아웃되었습니다.",
      });
    } catch (error) {
      console.error("Logout error:", error.message);
      
      return reply.status(500).send({
        success: false,
        message: "로그아웃 중 오류가 발생했습니다.",
      });
    }
  });

  // 현재 사용자 정보 조회
  fastify.get("/me", {
    preHandler: [authenticateToken],
    schema: {
      response: {
        200: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            data: {
              type: "object",
              properties: {
                user_id: { type: "string" },
                username: { type: "string" },
                level: { type: "number" },
                total_quizzes: { type: "number" },
                created_at: { type: "string" },
                last_login_at: { type: "string" },
              },
            },
          },
        },
      },
    },
  }, async (request, reply) => {
    try {
      const userId = request.user.userId;
      const user = await getUserById(userId);

      if (!user) {
        return reply.status(404).send({
          success: false,
          message: "사용자를 찾을 수 없습니다.",
        });
      }

      // 비밀번호 해시 제외하고 반환
      const { password_hash, ...userWithoutPassword } = user;

      return reply.status(200).send({
        success: true,
        data: userWithoutPassword,
      });
    } catch (error) {
      console.error("Get user info error:", error.message);
      
      return reply.status(500).send({
        success: false,
        message: "사용자 정보 조회 중 오류가 발생했습니다.",
      });
    }
  });

  // 토큰 갱신
  fastify.post("/refresh", {
    schema: {
      body: {
        type: "object",
        required: ["refreshToken"],
        properties: {
          refreshToken: {
            type: "string",
          },
        },
      },
      response: {
        200: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            data: {
              type: "object",
              properties: {
                accessToken: { type: "string" },
                refreshToken: { type: "string" },
              },
            },
          },
        },
      },
    },
  }, async (request, reply) => {
    try {
      const { refreshToken } = request.body;

      // 토큰 검증 및 갱신
      const newTokens = await verifyAndRefreshToken(refreshToken);

      return reply.status(200).send({
        success: true,
        data: newTokens,
      });
    } catch (error) {
      console.error("Token refresh error:", error.message);
      
      return reply.status(401).send({
        success: false,
        message: "유효하지 않은 refresh token입니다.",
      });
    }
  });

  // 닉네임 변경
  fastify.put("/username", {
    preHandler: [authenticateToken],
    schema: {
      body: {
        type: "object",
        required: ["newUsername", "password"],
        properties: {
          newUsername: {
            type: "string",
            minLength: 3,
            maxLength: 20,
            pattern: "^[a-zA-Z0-9_]+$",
          },
          password: {
            type: "string",
            minLength: 4,
          },
        },
      },
      response: {
        200: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            data: {
              type: "object",
              properties: {
                user_id: { type: "string" },
                username: { type: "string" },
                level: { type: "number" },
                total_quizzes: { type: "number" },
                username_changed_at: { type: "string" },
              },
            },
          },
        },
      },
    },
  }, async (request, reply) => {
    try {
      const { newUsername, password } = request.body;
      const userId = request.user.userId;

      // 닉네임 변경
      const updatedUser = await updateUsername(userId, newUsername, password);

      return reply.status(200).send({
        success: true,
        data: updatedUser,
      });
    } catch (error) {
      console.error("Username update error:", error.message);
      
      return reply.status(400).send({
        success: false,
        message: error.message,
      });
    }
  });

  // 비밀번호 변경
  fastify.put("/password", {
    preHandler: [authenticateToken],
    schema: {
      body: {
        type: "object",
        required: ["currentPassword", "newPassword"],
        properties: {
          currentPassword: {
            type: "string",
            minLength: 4,
          },
          newPassword: {
            type: "string",
            minLength: 4,
          },
        },
      },
      response: {
        200: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            message: { type: "string" },
          },
        },
      },
    },
  }, async (request, reply) => {
    try {
      const { currentPassword, newPassword } = request.body;
      const userId = request.user.userId;

      // 비밀번호 변경
      await updatePassword(userId, currentPassword, newPassword);

      return reply.status(200).send({
        success: true,
        message: "비밀번호가 성공적으로 변경되었습니다.",
      });
    } catch (error) {
      console.error("Password update error:", error.message);
      
      return reply.status(400).send({
        success: false,
        message: error.message,
      });
    }
  });
}

module.exports = authRoutes;
