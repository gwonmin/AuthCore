# 멀티스테이지 빌드
FROM node:20-alpine AS builder

WORKDIR /app

# 의존성 파일 복사 (package.json과 package-lock.json)
COPY package.json package-lock.json* ./

# 의존성 설치 (package-lock.json이 있으면 npm ci, 없으면 npm install)
RUN if [ -f package-lock.json ]; then \
      npm ci --only=production; \
    else \
      npm install --only=production; \
    fi

# 소스 코드 복사
COPY . .

# 프로덕션 이미지
FROM node:20-alpine

WORKDIR /app

# 보안을 위해 non-root 사용자 생성
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# 의존성 및 소스 코드 복사
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --chown=nodejs:nodejs . .

# non-root 사용자로 전환
USER nodejs

# 포트 노출
EXPOSE 4000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:4000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# 애플리케이션 실행
CMD ["node", "src/index.js"]

