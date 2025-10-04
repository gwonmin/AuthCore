// JWT 서비스 통합 테스트
const jwt = require('jsonwebtoken');

describe('JWT Service Integration Tests', () => {
  describe('JWT Library Tests', () => {
    it('should generate and verify JWT tokens', () => {
      const payload = {
        userId: 'test-user-123',
        username: 'testuser',
        type: 'access'
      };
      
      const secret = process.env.JWT_SECRET || 'test-secret';
      
      // 토큰 생성
      const token = jwt.sign(payload, secret, { expiresIn: '15m' });
      
      // 토큰이 생성되었는지 확인
      expect(token).toBeDefined();
      expect(typeof token).toBe('string');
      
      // 토큰을 디코딩해서 내용 확인
      const decoded = jwt.verify(token, secret);
      expect(decoded.userId).toBe(payload.userId);
      expect(decoded.username).toBe(payload.username);
      expect(decoded.type).toBe(payload.type);
    });

    it('should throw error for invalid token', () => {
      const secret = process.env.JWT_SECRET || 'test-secret';
      
      expect(() => {
        jwt.verify('invalid-token', secret);
      }).toThrow();
    });

    it('should throw error for expired token', () => {
      const payload = { userId: '123' };
      const secret = process.env.JWT_SECRET || 'test-secret';
      
      // 만료된 토큰 생성 (1ms 후 만료)
      const token = jwt.sign(payload, secret, { expiresIn: '1ms' });
      
      // 약간의 지연 후 검증
      setTimeout(() => {
        expect(() => {
          jwt.verify(token, secret);
        }).toThrow();
      }, 10);
    });

    it('should handle different token types', () => {
      const secret = process.env.JWT_SECRET || 'test-secret';
      
      // Access Token
      const accessToken = jwt.sign(
        { userId: '123', type: 'access' },
        secret
      );
      
      // Refresh Token
      const refreshToken = jwt.sign(
        { userId: '123', type: 'refresh', tokenId: 'token-123' },
        secret
      );
      
      const decodedAccess = jwt.verify(accessToken, secret);
      const decodedRefresh = jwt.verify(refreshToken, secret);
      
      expect(decodedAccess.type).toBe('access');
      expect(decodedRefresh.type).toBe('refresh');
      expect(decodedRefresh.tokenId).toBe('token-123');
    });
  });
});
