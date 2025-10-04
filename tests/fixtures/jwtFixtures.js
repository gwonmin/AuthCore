// JWT 관련 테스트 픽스처

const mockAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIwNTgzOTY4OC05NmUxLTQyNzItYTQxOC04OTAzMDI4MmQ4MzIiLCJ1c2VybmFtZSI6InRlc3R1c2VyIiwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc1OTU1ODk0NSwiZXhwIjoxNzU5NTU5ODQ1fQ.i7fdhJisBuhTYn5wC6uaKQIUopxkKiSI64FO3tgrPQA';

const mockRefreshToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbklkIjoiMDI4ODliMjQtNmY1NS00NGJjLTk1MTUtYmEyNTEzOTE3NjExIiwidXNlcklkIjoiMDU4Mzk2ODgtOTZlMS00MjcyLWE0MTgtODkwMzAyODJkODMyIiwidHlwZSI6InJlZnJlc2giLCJpYXQiOjE3NTk1NTg5NDUsImV4cCI6MTc2MDE2Mzc0NX0.xsQIRXmqtpQ0LY8bbmTv_eDRg1JNAxBcBas2CgTPSX8';

const mockTokenPair = {
  accessToken: mockAccessToken,
  refreshToken: mockRefreshToken
};

const mockDecodedAccessToken = {
  userId: '05839688-96e1-4272-a418-89030282d832',
  username: 'testuser',
  type: 'access',
  iat: 1759558945,
  exp: 1759559845
};

const mockDecodedRefreshToken = {
  tokenId: '02889b24-6f55-44bc-9515-ba2513917611',
  userId: '05839688-96e1-4272-a418-89030282d832',
  type: 'refresh',
  iat: 1759558945,
  exp: 1760163745
};

const mockRefreshTokenRecord = {
  token_id: '02889b24-6f55-44bc-9515-ba2513917611',
  user_id: '05839688-96e1-4272-a418-89030282d832',
  token_hash: 'hashed-refresh-token',
  expires_at: 1760163745,
  created_at: '2025-10-04T06:16:21.969Z',
  is_revoked: false
};

module.exports = {
  mockAccessToken,
  mockRefreshToken,
  mockTokenPair,
  mockDecodedAccessToken,
  mockDecodedRefreshToken,
  mockRefreshTokenRecord
};
