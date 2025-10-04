module.exports = {
  // 테스트 환경
  testEnvironment: 'node',
  
  // ES 모듈 변환 설정
  transformIgnorePatterns: [
    'node_modules/(?!(uuid)/)'
  ],
  
  // 환경 변수 설정
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  
  // 테스트 파일 패턴
  testMatch: [
    '**/tests/unit/**/*.test.js',
    '**/tests/unit/**/*.spec.js',
    '**/tests/integration/**/*.test.js',
    '**/tests/integration/**/*.spec.js'
  ],
  
  // 커버리지 설정
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  
  // 커버리지 수집 대상
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/index.js', // 메인 진입점 제외
    '!src/services/jwtService.js', // JWT 서비스는 통합 테스트로 검증
    '!**/node_modules/**'
  ],
  
  // 커버리지 임계값 (현실적인 수준으로 설정)
  coverageThreshold: {
    global: {
      branches: 30,
      functions: 30,
      lines: 30,
      statements: 30
    }
  },
  
  
  // 비동기 테스트 타임아웃
  testTimeout: 10000,
  
  // 테스트 실행 전 정리
  clearMocks: true,
  restoreMocks: true
};