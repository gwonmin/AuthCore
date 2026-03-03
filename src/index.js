const fastify = require("fastify");
const cors = require("@fastify/cors");
const jwt = require("@fastify/jwt");
const rateLimit = require("@fastify/rate-limit");
const routes = require("./routes");
const { errorHandler, notFoundHandler } = require("./middleware/errorHandler");

require("dotenv").config();

const isProduction = process.env.NODE_ENV === "production";

function createApp() {
  const app = fastify({ logger: true });

  // CORS 설정
  app.register(cors, {
    origin: "*",
    methods: ["GET", "POST", "PUT", "DELETE"],
    credentials: true,
  });

  // Rate Limiting 설정
  app.register(rateLimit, {
    max: 100,
    timeWindow: "1 minute",
    errorResponseBuilder: function () {
      return {
        success: false,
        message: "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
      };
    },
  });

  // JWT 플러그인 등록
  const jwtSecret = process.env.JWT_SECRET;

  if (!jwtSecret && isProduction) {
    throw new Error("JWT_SECRET 환경 변수가 설정되어 있지 않습니다 (production).");
  }

  app.register(jwt, {
    // 로컬/테스트에서는 기본값 허용, 프로덕션에서는 위에서 강제
    secret: jwtSecret || "dev-only-jwt-secret",
  });

  // 에러 처리 등록
  app.setErrorHandler(errorHandler);
  app.setNotFoundHandler(notFoundHandler);

  // 라우트 등록
  app.register(routes);

  // 헬스체크 엔드포인트
  app.get("/health", async () => {
    return { status: "ok", service: "authcore" };
  });

  return app;
}

async function start() {
  try {
    const app = createApp();
    const port = process.env.PORT || 4000;
    const host = process.env.HOST || "0.0.0.0";

    console.log("🚀 Starting Fastify server...");
    await app.listen({ port, host });
    console.log(`✅ Server listening on ${host}:${port}`);
  } catch (err) {
    console.error("❌ Server failed to start:", err);
    process.exit(1);
  }
}

if (require.main === module) {
  // 직접 실행된 경우에만 서버 시작 (테스트/스크립트 재사용 가능)
  start();
}

module.exports = { createApp, start };
