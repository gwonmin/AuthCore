// authService 유닛테스트
const bcrypt = require('bcryptjs');

const {
  registerUser,
  loginUser,
  getUserByUsername,
  getUserById,
  updateUsername,
  updatePassword
} = require('../../src/services/authService');

const {
  mockUser,
  mockNewUser,
  mockLoginData,
  mockInvalidLoginData,
  mockUpdateUsernameData,
  mockUpdatePasswordData
} = require('../fixtures/userFixtures');

// DynamoDB 모킹
const mockDynamoDBClient = {
  send: jest.fn()
};

jest.mock('@aws-sdk/lib-dynamodb', () => ({
  DynamoDBDocumentClient: {
    from: jest.fn(() => mockDynamoDBClient)
  },
  PutCommand: jest.fn().mockImplementation((params) => ({ ...params, _command: 'PutCommand' })),
  GetCommand: jest.fn().mockImplementation((params) => ({ ...params, _command: 'GetCommand' })),
  UpdateCommand: jest.fn().mockImplementation((params) => ({ ...params, _command: 'UpdateCommand' })),
  QueryCommand: jest.fn().mockImplementation((params) => ({ ...params, _command: 'QueryCommand' }))
}));

// bcrypt 모킹
jest.mock('bcryptjs', () => ({
  hash: jest.fn(),
  compare: jest.fn()
}));

// uuid 모킹
jest.mock('uuid', () => ({
  v4: jest.fn(() => 'test-uuid-123')
}));

describe('userService', () => {
  beforeEach(() => {
    // bcrypt 모킹 설정
    bcrypt.hash.mockResolvedValue('hashed-password');
    bcrypt.compare.mockResolvedValue(true);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('registerUser', () => {
    it('새 사용자를 성공적으로 등록해야 함', async () => {
      // Given
      mockDynamoDBClient.send
        .mockResolvedValueOnce({ Items: [] }) // 닉네임 중복 검사 - 중복 없음
        .mockResolvedValueOnce({}); // 사용자 등록 성공

      // When
      const result = await registerUser(mockNewUser.username, mockNewUser.password, mockDynamoDBClient);

      // Then
      expect(result).toMatchObject({
        user_id: 'test-uuid-123',
        username: mockNewUser.username,
        is_active: true
      });
      expect(result.password_hash).toBeUndefined();
      expect(bcrypt.hash).toHaveBeenCalledWith(mockNewUser.password, 10);
    });

    it('닉네임이 3자 미만이면 에러를 던져야 함', async () => {
      // When & Then
      await expect(registerUser('ab', 'password123', mockDynamoDBClient))
        .rejects.toThrow('닉네임은 3-20자 사이여야 합니다.');
    });

    it('닉네임이 20자를 초과하면 에러를 던져야 함', async () => {
      // When & Then
      await expect(registerUser('a'.repeat(21), 'password123', mockDynamoDBClient))
        .rejects.toThrow('닉네임은 3-20자 사이여야 합니다.');
    });

    it('비밀번호가 4자 미만이면 에러를 던져야 함', async () => {
      // When & Then
      await expect(registerUser('testuser', '123', mockDynamoDBClient))
        .rejects.toThrow('비밀번호는 4자 이상이어야 합니다.');
    });

    it('이미 존재하는 닉네임이면 에러를 던져야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Items: [mockUser] }); // 닉네임 중복

      // When & Then
      await expect(registerUser(mockNewUser.username, mockNewUser.password, mockDynamoDBClient))
        .rejects.toThrow('이미 사용 중인 닉네임입니다.');
    });
  });

  describe('loginUser', () => {
    it('유효한 자격증명으로 로그인해야 함', async () => {
      // Given
      mockDynamoDBClient.send
        .mockResolvedValueOnce({ Items: [mockUser] }) // 사용자 조회
        .mockResolvedValueOnce({}); // 마지막 로그인 시간 업데이트

      // When
      const result = await loginUser(mockLoginData.username, mockLoginData.password, mockDynamoDBClient);

      // Then
      expect(result).toMatchObject({
        user_id: mockUser.user_id,
        username: mockUser.username,
        is_active: true
      });
      expect(result.password_hash).toBeUndefined();
      expect(bcrypt.compare).toHaveBeenCalledWith(mockLoginData.password, mockUser.password_hash);
    });

    it('존재하지 않는 사용자면 에러를 던져야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Items: [] }); // 사용자 없음

      // When & Then
      await expect(loginUser(mockLoginData.username, mockLoginData.password, mockDynamoDBClient))
        .rejects.toThrow('존재하지 않는 사용자입니다.');
    });

    it('비활성화된 계정이면 에러를 던져야 함', async () => {
      // Given
      const inactiveUser = { ...mockUser, is_active: false };
      mockDynamoDBClient.send.mockResolvedValueOnce({ Items: [inactiveUser] });

      // When & Then
      await expect(loginUser(mockLoginData.username, mockLoginData.password, mockDynamoDBClient))
        .rejects.toThrow('비활성화된 계정입니다.');
    });

    it('잘못된 비밀번호면 에러를 던져야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Items: [mockUser] });
      bcrypt.compare.mockResolvedValueOnce(false); // 비밀번호 불일치

      // When & Then
      await expect(loginUser(mockLoginData.username, mockInvalidLoginData.password, mockDynamoDBClient))
        .rejects.toThrow('비밀번호가 일치하지 않습니다.');
    });
  });

  describe('getUserByUsername', () => {
    it('닉네임으로 사용자를 조회해야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Items: [mockUser] });

      // When
      const result = await getUserByUsername(mockUser.username, mockDynamoDBClient);

      // Then
      expect(result).toEqual(mockUser);
      expect(mockDynamoDBClient.send).toHaveBeenCalledWith(
        expect.any(Object)
      );
    });

    it('사용자가 없으면 null을 반환해야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Items: [] });

      // When
      const result = await getUserByUsername('nonexistent', mockDynamoDBClient);

      // Then
      expect(result).toBeNull();
    });
  });

  describe('getUserById', () => {
    it('사용자 ID로 사용자를 조회해야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Item: mockUser });

      // When
      const result = await getUserById(mockUser.user_id, mockDynamoDBClient);

      // Then
      expect(result).toEqual(mockUser);
    });

    it('사용자가 없으면 null을 반환해야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Item: null });

      // When
      const result = await getUserById('nonexistent-id', mockDynamoDBClient);

      // Then
      expect(result).toBeNull();
    });
  });

  describe('updateUsername', () => {
    it('닉네임을 성공적으로 변경해야 함', async () => {
      // Given
      const updatedUser = { ...mockUser, username: mockUpdateUsernameData.newUsername };
      mockDynamoDBClient.send
        .mockResolvedValueOnce({ Item: mockUser }) // 사용자 조회
        .mockResolvedValueOnce({ Items: [] }) // 새 닉네임 중복 검사
        .mockResolvedValueOnce({}) // 닉네임 업데이트
        .mockResolvedValueOnce({ Item: updatedUser }); // 업데이트된 사용자 조회

      // When
      const result = await updateUsername(
        mockUser.user_id,
        mockUpdateUsernameData.newUsername,
        mockUpdateUsernameData.password,
        mockDynamoDBClient
      );

      // Then
      expect(result).toMatchObject({
        user_id: mockUser.user_id,
        username: mockUpdateUsernameData.newUsername
      });
      expect(bcrypt.compare).toHaveBeenCalledWith(
        mockUpdateUsernameData.password,
        mockUser.password_hash
      );
    });

    it('현재 비밀번호가 틀리면 에러를 던져야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Item: mockUser });
      bcrypt.compare.mockResolvedValueOnce(false);

      // When & Then
      await expect(updateUsername(
        mockUser.user_id,
        mockUpdateUsernameData.newUsername,
        'wrongpassword',
        mockDynamoDBClient
      )).rejects.toThrow('비밀번호가 일치하지 않습니다.');
    });
  });

  describe('updatePassword', () => {
    it('비밀번호를 성공적으로 변경해야 함', async () => {
      // Given
      mockDynamoDBClient.send
        .mockResolvedValueOnce({ Item: mockUser }) // 사용자 조회
        .mockResolvedValueOnce({}) // 비밀번호 업데이트
        .mockResolvedValueOnce({ Item: mockUser }); // 업데이트된 사용자 조회

      // When
      const result = await updatePassword(
        mockUser.user_id,
        mockUpdatePasswordData.currentPassword,
        mockUpdatePasswordData.newPassword,
        mockDynamoDBClient
      );

      // Then
      expect(result).toMatchObject({
        user_id: mockUser.user_id,
        username: mockUser.username
      });
      expect(bcrypt.hash).toHaveBeenCalledWith(mockUpdatePasswordData.newPassword, 10);
    });

    it('현재 비밀번호가 틀리면 에러를 던져야 함', async () => {
      // Given
      mockDynamoDBClient.send.mockResolvedValueOnce({ Item: mockUser });
      bcrypt.compare.mockResolvedValueOnce(false);

      // When & Then
      await expect(updatePassword(
        mockUser.user_id,
        'wrongpassword',
        mockUpdatePasswordData.newPassword,
        mockDynamoDBClient
      )).rejects.toThrow('현재 비밀번호가 일치하지 않습니다.');
    });
  });
});