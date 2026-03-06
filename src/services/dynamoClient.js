const {
  DynamoDBDocumentClient,
} = require("@aws-sdk/lib-dynamodb");
const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");

const { AWS_REGION = "ap-northeast-2" } = process.env;

const logger = {
  info: (message) => console.log(`[DYNAMO_CLIENT] ${message}`),
  error: (message) => console.error(`[DYNAMO_CLIENT] ${message}`),
};

/**
 * DynamoDB DocumentClient 생성 헬퍼
 * @param {Object} options - DynamoDB 클라이언트 옵션
 * @returns {DynamoDBDocumentClient}
 */
function createDynamoDBClient(options = {}) {
  try {
    const client = new DynamoDBClient({
      region: AWS_REGION,
      ...options,
    });
    logger.info("DynamoDB client created");
    return DynamoDBDocumentClient.from(client);
  } catch (error) {
    logger.error(`Failed to create DynamoDB client: ${error.message}`);
    throw new Error("Failed to initialize DynamoDB client");
  }
}

module.exports = {
  createDynamoDBClient,
};

