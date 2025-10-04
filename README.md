# 🔐 AuthCore

여러 플랫폼에 연동 가능한 인증 서비스를 제공하는 서버리스 API입니다.  
DynamoDB를 백엔드 DB로 사용하며, AWS API Gateway + Lambda에 배포됩니다.

---

## 🛠️ 기술 스택

- **Fastify** (`^4.21.0`) – 고성능 Node.js 웹 프레임워크  
- **AWS Lambda + API Gateway** – 완전한 서버리스 인프라  
- **DynamoDB** – 무중단 NoSQL 데이터베이스  
- **JWT** – JSON Web Token 기반 인증  
- **bcryptjs** – 비밀번호 해싱  
- **@aws-sdk v3** – 최신 AWS SDK (DynamoDB client)  
- **serverless-http** – Lambda에 Fastify 핸들러 연결  
