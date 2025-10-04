// 사용자 관련 테스트 픽스처

const mockUser = {
  user_id: '05839688-96e1-4272-a418-89030282d832',
  username: 'testuser',
  password_hash: '$2a$10$test.hash.here',
  created_at: '2025-10-04T06:16:21.969Z',
  last_login_at: '2025-10-04T06:21:02.367Z',
  is_active: true
};

const mockUserWithoutPassword = {
  user_id: '05839688-96e1-4272-a418-89030282d832',
  username: 'testuser',
  created_at: '2025-10-04T06:16:21.969Z',
  last_login_at: '2025-10-04T06:21:02.367Z',
  is_active: true
};

const mockNewUser = {
  username: 'newuser',
  password: 'newpass123'
};

const mockLoginData = {
  username: 'testuser',
  password: 'testpass123'
};

const mockInvalidLoginData = {
  username: 'testuser',
  password: 'wrongpassword'
};

const mockUpdateUsernameData = {
  newUsername: 'updateduser',
  password: 'testpass123'
};

const mockUpdatePasswordData = {
  currentPassword: 'testpass123',
  newPassword: 'newpass123'
};

module.exports = {
  mockUser,
  mockUserWithoutPassword,
  mockNewUser,
  mockLoginData,
  mockInvalidLoginData,
  mockUpdateUsernameData,
  mockUpdatePasswordData
};
