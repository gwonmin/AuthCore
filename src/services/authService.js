const {
  DynamoDBDocumentClient,
  PutCommand,
  GetCommand,
  UpdateCommand,
  QueryCommand,
} = require("@aws-sdk/lib-dynamodb");
const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const bcrypt = require("bcryptjs");
const { v4: uuidv4 } = require("uuid");
const jwt = require("jsonwebtoken");
const { TABLES, JWT_CONFIG, ERROR_MESSAGES } = require("../config/constants");
const { validateUsername, validatePassword, sanitizeUser } = require("../utils/validation");

// 환경 변수 설정
const { 
  AWS_REGION = "ap-northeast-2",
  JWT_SECRET = "your-super-secret-jwt-key-change-this-in-production"
} = process.env;

// 로깅 설정
const logger = {
  info: (message) => console.log(`[AUTH_SERVICE] ${message}`),
  error: (message) => console.error(`[AUTH_SERVICE] ${message}`),
};

/**
 * DynamoDB 클라이언트 생성
 */
function createDynamoDBClient(options = {}) {
  try {
    const client = new DynamoDBClient({
      region: AWS_REGION,
      ...options,
    });
    return DynamoDBDocumentClient.from(client);
  } catch (error) {
    logger.error(`Failed to create DynamoDB client: ${error.message}`);
    throw new Error("Failed to initialize DynamoDB client");
  }
}

// 기본 DynamoDB 클라이언트 인스턴스 (테스트에서는 모킹됨)
let dynamoDB = null;

// DynamoDB 클라이언트 초기화 함수
function initializeDynamoDB() {
  if (process.env.NODE_ENV !== 'test') {
    try {
      dynamoDB = createDynamoDBClient();
      logger.info('DynamoDB client initialized successfully');
    } catch (error) {
      logger.error(`Failed to initialize DynamoDB client: ${error.message}`);
      dynamoDB = null;
    }
  }
}

// 초기화 실행
initializeDynamoDB();

/**
 * 사용자 회원가입
 * @param {string} username - 사용자 닉네임
 * @param {string} password - 비밀번호
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<Object>} 생성된 사용자 정보
 */
async function registerUser(username, password, dynamoDBClient = dynamoDB) {
  try {
    // 입력값 검증
    const usernameValidation = validateUsername(username);
    if (!usernameValidation.isValid) {
      throw new Error(usernameValidation.error);
    }

    const passwordValidation = validatePassword(password);
    if (!passwordValidation.isValid) {
      throw new Error(passwordValidation.error);
    }

    // 닉네임 중복 검사
    const existingUser = await getUserByUsername(username, dynamoDBClient);
    if (existingUser) {
      throw new Error(ERROR_MESSAGES.USERNAME_DUPLICATE);
    }

    // 비밀번호 해싱
    const saltRounds = 10;
    const passwordHash = await bcrypt.hash(password, saltRounds);

    // 사용자 데이터 생성
    const userId = uuidv4();
    const now = new Date().toISOString();
    
    const userData = {
      user_id: userId,
      username: username,
      password_hash: passwordHash,
      created_at: now,
      last_login_at: now,
      is_active: true,
    };

    // DynamoDB에 저장
    await dynamoDBClient.send(
      new PutCommand({
        TableName: TABLES.USERS,
        Item: userData,
        ConditionExpression: "attribute_not_exists(user_id)", // 중복 방지
      })
    );

    logger.info(`User registered: ${username}`);
    
    // 비밀번호 해시 제외하고 반환
    return sanitizeUser(userData);
  } catch (error) {
    logger.error(`Failed to register user: ${error.message}`);
    throw error;
  }
}

/**
 * 사용자 로그인
 * @param {string} username - 사용자 닉네임
 * @param {string} password - 비밀번호
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<Object>} 사용자 정보
 */
async function loginUser(username, password, dynamoDBClient = dynamoDB) {
  try {
    // 사용자 조회
    const user = await getUserByUsername(username, dynamoDBClient);
    if (!user) {
      throw new Error("존재하지 않는 사용자입니다.");
    }

    if (!user.is_active) {
      throw new Error("비활성화된 계정입니다.");
    }

    // 비밀번호 검증
    const isValidPassword = await bcrypt.compare(password, user.password_hash);
    if (!isValidPassword) {
      throw new Error("비밀번호가 일치하지 않습니다.");
    }

    // 마지막 로그인 시간 업데이트
    const now = new Date().toISOString();
    await dynamoDBClient.send(
      new UpdateCommand({
        TableName: TABLES.USERS,
        Key: { user_id: user.user_id },
        UpdateExpression: "SET last_login_at = :login_time",
        ExpressionAttributeValues: {
          ":login_time": now,
        },
      })
    );

    logger.info(`User logged in: ${username}`);
    
    // 비밀번호 해시 제외하고 반환
    const { password_hash, ...userWithoutPassword } = user;
    return { ...userWithoutPassword, last_login_at: now };
  } catch (error) {
    logger.error(`Failed to login user: ${error.message}`);
    throw error;
  }
}

/**
 * 닉네임으로 사용자 조회
 * @param {string} username - 사용자 닉네임
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<Object|null>} 사용자 정보
 */
async function getUserByUsername(username, dynamoDBClient = dynamoDB) {
  try {
    const result = await dynamoDBClient.send(
      new QueryCommand({
        TableName: TABLES.USERS,
        IndexName: "username-index",
        KeyConditionExpression: "username = :username",
        ExpressionAttributeValues: {
          ":username": username,
        },
      })
    );

    return result.Items && result.Items.length > 0 ? result.Items[0] : null;
  } catch (error) {
    logger.error(`Failed to get user by username: ${error.message}`);
    throw error;
  }
}

/**
 * 사용자 ID로 사용자 조회
 * @param {string} userId - 사용자 ID
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<Object|null>} 사용자 정보
 */
async function getUserById(userId, dynamoDBClient = dynamoDB) {
  try {
    const result = await dynamoDBClient.send(
      new GetCommand({
        TableName: TABLES.USERS,
        Key: { user_id: userId },
      })
    );

    return result.Item || null;
  } catch (error) {
    logger.error(`Failed to get user by ID: ${error.message}`);
    throw error;
  }
}

/**
 * 닉네임 변경
 * @param {string} userId - 사용자 ID
 * @param {string} newUsername - 새 닉네임
 * @param {string} password - 현재 비밀번호
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<Object>} 업데이트된 사용자 정보
 */
async function updateUsername(userId, newUsername, password, dynamoDBClient = dynamoDB) {
  try {
    // 입력값 검증
    if (!newUsername || newUsername.length < 3 || newUsername.length > 20) {
      throw new Error("닉네임은 3-20자 사이여야 합니다.");
    }

    // 사용자 조회
    const user = await getUserById(userId, dynamoDBClient);
    if (!user) {
      throw new Error("사용자를 찾을 수 없습니다.");
    }

    // 비밀번호 검증
    const isValidPassword = await bcrypt.compare(password, user.password_hash);
    if (!isValidPassword) {
      throw new Error("비밀번호가 일치하지 않습니다.");
    }

    // 새 닉네임 중복 검사
    const existingUser = await getUserByUsername(newUsername, dynamoDBClient);
    if (existingUser && existingUser.user_id !== userId) {
      throw new Error("이미 사용 중인 닉네임입니다.");
    }

    // 닉네임 업데이트
    const now = new Date().toISOString();
    await dynamoDBClient.send(
      new UpdateCommand({
        TableName: TABLES.USERS,
        Key: { user_id: userId },
        UpdateExpression: "SET username = :new_username, username_changed_at = :changed_time",
        ExpressionAttributeValues: {
          ":new_username": newUsername,
          ":changed_time": now,
        },
      })
    );

    logger.info(`Username updated for user: ${userId}`);
    
    // 업데이트된 사용자 정보 반환
    const updatedUser = await getUserById(userId, dynamoDBClient);
    const { password_hash, ...userWithoutPassword } = updatedUser;
    return userWithoutPassword;
  } catch (error) {
    logger.error(`Failed to update username: ${error.message}`);
    throw error;
  }
}

/**
 * 비밀번호 변경
 * @param {string} userId - 사용자 ID
 * @param {string} currentPassword - 현재 비밀번호
 * @param {string} newPassword - 새 비밀번호
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<Object>} 업데이트된 사용자 정보
 */
async function updatePassword(userId, currentPassword, newPassword, dynamoDBClient = dynamoDB) {
  try {
    // 입력값 검증
    if (!newPassword || newPassword.length < 4) {
      throw new Error("새 비밀번호는 4자 이상이어야 합니다.");
    }

    // 사용자 조회
    const user = await getUserById(userId, dynamoDBClient);
    if (!user) {
      throw new Error("사용자를 찾을 수 없습니다.");
    }

    // 현재 비밀번호 검증
    const isValidPassword = await bcrypt.compare(currentPassword, user.password_hash);
    if (!isValidPassword) {
      throw new Error("현재 비밀번호가 일치하지 않습니다.");
    }

    // 새 비밀번호 해싱
    const saltRounds = 10;
    const newPasswordHash = await bcrypt.hash(newPassword, saltRounds);

    // 비밀번호 업데이트
    await dynamoDBClient.send(
      new UpdateCommand({
        TableName: TABLES.USERS,
        Key: { user_id: userId },
        UpdateExpression: "SET password_hash = :new_password_hash",
        ExpressionAttributeValues: {
          ":new_password_hash": newPasswordHash,
        },
      })
    );

    logger.info(`Password updated for user: ${userId}`);
    
    // 업데이트된 사용자 정보 반환
    const updatedUser = await getUserById(userId, dynamoDBClient);
    const { password_hash, ...userWithoutPassword } = updatedUser;
    return userWithoutPassword;
  } catch (error) {
    logger.error(`Failed to update password: ${error.message}`);
    throw error;
  }
}

/**
 * Access Token 생성
 * @param {string} userId - 사용자 ID
 * @param {string} username - 사용자 닉네임
 * @returns {string} Access Token
 */
function generateAccessToken(userId, username) {
  try {
    const payload = {
      userId,
      username,
      type: "access",
    };

    const token = jwt.sign(payload, JWT_SECRET, {
      expiresIn: JWT_CONFIG.ACCESS_EXPIRES_IN,
    });

    logger.info(`Access token generated for user: ${username}`);
    return token;
  } catch (error) {
    logger.error(`Failed to generate access token: ${error.message}`);
    throw new Error("Failed to generate access token");
  }
}

/**
 * Refresh Token 생성 및 저장
 * @param {string} userId - 사용자 ID
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<string>} Refresh Token
 */
async function generateRefreshToken(userId, dynamoDBClient = dynamoDB) {
  try {
    const tokenId = uuidv4();
    const token = jwt.sign(
      { tokenId, userId, type: "refresh" },
      JWT_SECRET,
      { expiresIn: JWT_CONFIG.REFRESH_EXPIRES_IN }
    );

    // 토큰 해시 생성 (저장용)
    const tokenHash = require("crypto")
      .createHash("sha256")
      .update(token)
      .digest("hex");

    // 만료 시간 계산
    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + 7); // 7일 후

    // DynamoDB에 저장
    await dynamoDBClient.send(
      new PutCommand({
        TableName: TABLES.REFRESH_TOKENS,
        Item: {
          token_id: tokenId,
          user_id: userId,
          token_hash: tokenHash,
          expires_at: Math.floor(expiresAt.getTime() / 1000), // TTL용 Unix timestamp
          created_at: new Date().toISOString(),
          is_revoked: false,
        },
      })
    );

    logger.info(`Refresh token generated for user: ${userId}`);
    return token;
  } catch (error) {
    logger.error(`Failed to generate refresh token: ${error.message}`);
    throw new Error("Failed to generate refresh token");
  }
}

/**
 * 토큰 쌍 생성 (Access + Refresh)
 * @param {string} userId - 사용자 ID
 * @param {string} username - 사용자 닉네임
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<Object>} 토큰 쌍
 */
async function generateTokenPair(userId, username, dynamoDBClient = dynamoDB) {
  try {
    const accessToken = generateAccessToken(userId, username);
    const refreshToken = await generateRefreshToken(userId, dynamoDBClient);

    return {
      accessToken,
      refreshToken,
    };
  } catch (error) {
    logger.error(`Failed to generate token pair: ${error.message}`);
    throw error;
  }
}

/**
 * Access Token 검증
 * @param {string} token - Access Token
 * @returns {Object} 디코딩된 토큰 페이로드
 */
function verifyAccessToken(token) {
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    
    if (decoded.type !== "access") {
      throw new Error("Invalid token type");
    }

    return decoded;
  } catch (error) {
    logger.error(`Failed to verify access token: ${error.message}`);
    throw new Error("Invalid access token");
  }
}

/**
 * Refresh Token 검증 및 갱신
 * @param {string} token - Refresh Token
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<Object>} 새로운 토큰 쌍
 */
async function verifyAndRefreshToken(token, dynamoDBClient = dynamoDB) {
  try {
    // 토큰 디코딩
    const decoded = jwt.verify(token, JWT_SECRET);
    
    if (decoded.type !== "refresh") {
      throw new Error("Invalid token type");
    }

    // DB에서 토큰 조회
    const tokenRecord = await dynamoDBClient.send(
      new GetCommand({
        TableName: TABLES.REFRESH_TOKENS,
        Key: { token_id: decoded.tokenId },
      })
    );

    if (!tokenRecord.Item) {
      throw new Error("Refresh token not found");
    }

    if (tokenRecord.Item.is_revoked) {
      throw new Error("Refresh token has been revoked");
    }

    // 토큰 해시 검증
    const tokenHash = require("crypto")
      .createHash("sha256")
      .update(token)
      .digest("hex");

    if (tokenRecord.Item.token_hash !== tokenHash) {
      throw new Error("Invalid refresh token");
    }

    // 기존 refresh token 무효화
    await revokeRefreshToken(decoded.tokenId, dynamoDBClient);

    // 사용자 정보 조회
    const user = await getUserById(decoded.userId, dynamoDBClient);
    if (!user) {
      throw new Error("User not found");
    }

    // 새 토큰 쌍 생성
    const newTokens = await generateTokenPair(decoded.userId, user.username, dynamoDBClient);
    
    logger.info(`Tokens refreshed for user: ${decoded.userId}`);
    return newTokens;
  } catch (error) {
    logger.error(`Failed to verify and refresh token: ${error.message}`);
    throw new Error("Invalid refresh token");
  }
}

/**
 * Refresh Token 무효화
 * @param {string} tokenId - 토큰 ID
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<void>}
 */
async function revokeRefreshToken(tokenId, dynamoDBClient = dynamoDB) {
  try {
    await dynamoDBClient.send(
      new UpdateCommand({
        TableName: TABLES.REFRESH_TOKENS,
        Key: { token_id: tokenId },
        UpdateExpression: "SET is_revoked = :revoked",
        ExpressionAttributeValues: {
          ":revoked": true,
        },
      })
    );

    logger.info(`Refresh token revoked: ${tokenId}`);
  } catch (error) {
    logger.error(`Failed to revoke refresh token: ${error.message}`);
    throw error;
  }
}

/**
 * 사용자의 모든 Refresh Token 무효화
 * @param {string} userId - 사용자 ID
 * @param {Object} dynamoDBClient - DynamoDB 클라이언트 (테스트용)
 * @returns {Promise<void>}
 */
async function revokeAllUserTokens(userId, dynamoDBClient = dynamoDB) {
  try {
    // 사용자의 모든 refresh token 조회
    const result = await dynamoDBClient.send(
      new QueryCommand({
        TableName: TABLES.REFRESH_TOKENS,
        IndexName: "user-id-index",
        KeyConditionExpression: "user_id = :userId",
        ExpressionAttributeValues: {
          ":userId": userId,
        },
      })
    );

    // 모든 토큰 무효화
    if (result.Items && result.Items.length > 0) {
      const revokePromises = result.Items.map(item =>
        revokeRefreshToken(item.token_id, dynamoDBClient)
      );

      await Promise.all(revokePromises);
    }
    
    logger.info(`All tokens revoked for user: ${userId}`);
  } catch (error) {
    logger.error(`Failed to revoke all user tokens: ${error.message}`);
    throw error;
  }
}

module.exports = {
  // 사용자 관리
  registerUser,
  loginUser,
  getUserByUsername,
  getUserById,
  updateUsername,
  updatePassword,
  
  // 토큰 관리
  generateAccessToken,
  generateRefreshToken,
  generateTokenPair,
  verifyAccessToken,
  verifyAndRefreshToken,
  revokeRefreshToken,
  revokeAllUserTokens,
  
  // 유틸리티
  createDynamoDBClient,
  logger,
};
