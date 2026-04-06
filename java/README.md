# Java 版 - 多Agent智能会议助手

> 使用 Spring Boot 3 + LangGraph4j + CompletableFuture 实现

## 技术栈

- **Agent框架**: LangGraph4j (状态图编排)
- **并行执行**: CompletableFuture (Fan-out/Fan-in)
- **Web框架**: Spring Boot 3 + Spring WebSocket
- **LLM**: MiniMax M2.7 / OpenAI (通过 OkHttp)
- **数据库**: H2 (开发) / PostgreSQL (生产)

## 快速开始

```bash
# 1. Maven 构建
mvn clean package -DskipTests

# 2. 运行
java -jar target/meeting-assistant-1.0.0.jar

# 3. 测试演示模式
curl -X POST http://localhost:8080/api/v1/meeting/demo/demo
```

## 项目结构

```
java/
├── src/main/java/com/meeting/
│   ├── agent/                    # 5个Agent实现
│   │   ├── TranscriptionAgent.java
│   │   ├── SummaryAgent.java
│   │   ├── ActionAgent.java
│   │   ├── InsightAgent.java
│   │   └── FollowUpAgent.java
│   ├── graph/
│   │   └── MeetingGraph.java     # Pipeline + 并行编排
│   ├── integration/
│   │   ├── MiniMaxClient.java    # MiniMax LLM
│   │   └── JiraIntegration.java  # Jira Cloud
│   ├── model/                    # 数据模型
│   └── websocket/
│       └── MeetingController.java # REST API
└── pom.xml
```
