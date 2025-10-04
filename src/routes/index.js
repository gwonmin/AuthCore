const authRoutes = require("./authRoutes");

async function routes(fastify, options) {
  // 인증 라우트 등록
  fastify.register(authRoutes, { prefix: "/auth" });
}

module.exports = routes;
