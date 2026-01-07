const fastify = require("fastify")({ logger: true });
const cors = require("@fastify/cors");
const jwt = require("@fastify/jwt");
const rateLimit = require("@fastify/rate-limit");
const routes = require("./routes");
const { errorHandler, notFoundHandler } = require("./middleware/errorHandler");
require("dotenv").config();

// CORS 설정
fastify.register(cors, {
  origin: "*",
  methods: ["GET", "POST", "PUT", "DELETE"],
  credentials: true,
});

// Rate Limiting 설정
fastify.register(rateLimit, {
  max: 100, // 최대 요청 수
  timeWindow: "1 minute", // 시간 윈도우
  errorResponseBuilder: function (request, context) {
    return {
      success: false,
      message: "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
    };
  },
});

// JWT 플러그인 등록
fastify.register(jwt, {
  secret: process.env.JWT_SECRET || "your-super-secret-jwt-key-change-this-in-production",
});

// 에러 처리 등록
fastify.setErrorHandler(errorHandler);
fastify.setNotFoundHandler(notFoundHandler);

// 라우트 등록
fastify.register(routes);

// 헬스체크 엔드포인트
fastify.get("/health", async (request, reply) => {
  return { status: "ok", service: "authcore" };
});

// 서버 시작
const start = async () => {
  try {
    const port = process.env.PORT || 4000;
    const host = process.env.HOST || "0.0.0.0";
    
    console.log("🚀 Starting Fastify server...");
    await fastify.listen({ port, host });
    console.log(`✅ Server listening on ${host}:${port}`);
  } catch (err) {
    console.error("❌ Server failed to start:", err);
    process.exit(1);
  }
};

// 애플리케이션 시작
start();
