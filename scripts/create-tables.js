const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { CreateTableCommand } = require("@aws-sdk/client-dynamodb");

const client = new DynamoDBClient({ region: "ap-northeast-2" });

async function createUsersTable() {
  const params = {
    TableName: "AuthCore_Users",
    KeySchema: [
      { AttributeName: "user_id", KeyType: "HASH" }, // Partition key
    ],
    AttributeDefinitions: [
      { AttributeName: "user_id", AttributeType: "S" },
      { AttributeName: "username", AttributeType: "S" },
    ],
    GlobalSecondaryIndexes: [
      {
        IndexName: "username-index",
        KeySchema: [{ AttributeName: "username", KeyType: "HASH" }],
        Projection: {
          ProjectionType: "ALL",
        },
        ProvisionedThroughput: {
          ReadCapacityUnits: 5,
          WriteCapacityUnits: 5,
        },
      },
    ],
    ProvisionedThroughput: {
      ReadCapacityUnits: 5,
      WriteCapacityUnits: 5,
    },
  };

  try {
    await client.send(new CreateTableCommand(params));
    console.log("✅ AuthCore_Users 테이블이 생성되었습니다.");
  } catch (error) {
    if (error.name === "ResourceInUseException") {
      console.log("ℹ️  AuthCore_Users 테이블이 이미 존재합니다.");
    } else {
      console.error("❌ AuthCore_Users 테이블 생성 실패:", error.message);
    }
  }
}

async function createRefreshTokensTable() {
  const params = {
    TableName: "AuthCore_RefreshTokens",
    KeySchema: [
      { AttributeName: "token_id", KeyType: "HASH" }, // Partition key
    ],
    AttributeDefinitions: [
      { AttributeName: "token_id", AttributeType: "S" },
      { AttributeName: "user_id", AttributeType: "S" },
    ],
    GlobalSecondaryIndexes: [
      {
        IndexName: "user-id-index",
        KeySchema: [{ AttributeName: "user_id", KeyType: "HASH" }],
        Projection: {
          ProjectionType: "ALL",
        },
        ProvisionedThroughput: {
          ReadCapacityUnits: 5,
          WriteCapacityUnits: 5,
        },
      },
    ],
    ProvisionedThroughput: {
      ReadCapacityUnits: 5,
      WriteCapacityUnits: 5,
    },
    TimeToLiveSpecification: {
      AttributeName: "expires_at",
      Enabled: true,
    },
  };

  try {
    await client.send(new CreateTableCommand(params));
    console.log("✅ AuthCore_RefreshTokens 테이블이 생성되었습니다.");
  } catch (error) {
    if (error.name === "ResourceInUseException") {
      console.log("ℹ️  AuthCore_RefreshTokens 테이블이 이미 존재합니다.");
    } else {
      console.error(
        "❌ AuthCore_RefreshTokens 테이블 생성 실패:",
        error.message,
      );
    }
  }
}

async function createTables() {
  console.log("🚀 DynamoDB 테이블 생성을 시작합니다...\n");

  await createUsersTable();
  await createRefreshTokensTable();

  console.log("\n✅ 모든 테이블 생성이 완료되었습니다!");
  console.log("\n📋 생성된 테이블:");
  console.log("- AuthCore_Users (사용자 정보)");
  console.log("- AuthCore_RefreshTokens (리프레시 토큰)");
}

// 스크립트 실행
if (require.main === module) {
  createTables().catch(console.error);
}

module.exports = { createTables };
