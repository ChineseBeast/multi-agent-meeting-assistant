# Go 版 - 多Agent智能会议助手

> 使用 Eino ADK 思想 + goroutine/channel 并行 + Gin 实现

## 技术栈

- **并行编排**: goroutine + sync.WaitGroup (Fan-out/Fan-in)
- **Web框架**: Gin
- **WebSocket**: gorilla/websocket
- **LLM**: MiniMax API (HTTP 调用)

## 快速开始

```bash
# 1. 下载依赖
go mod download

# 2. 运行
go run ./cmd/

# 3. 测试演示模式
curl -X POST http://localhost:8090/api/v1/meeting/demo/demo
```

## 项目结构

```
golang/
├── cmd/
│   └── main.go                  # 入口 + Gin路由 + WebSocket
├── internal/
│   ├── agent/                   # 5个Agent实现
│   │   ├── transcription.go
│   │   ├── summary.go
│   │   ├── action.go
│   │   ├── insight.go
│   │   └── followup.go
│   ├── graph/
│   │   └── pipeline.go          # goroutine 并行编排
│   └── model/
│       └── types.go             # 数据类型
├── go.mod
└── README.md
```

## Go 版亮点

- **goroutine 并行**: 天然轻量级并发，三个Agent并行仅需 `sync.WaitGroup`
- **channel 通信**: 可扩展为流式传输
- **高性能**: 编译后单二进制，启动快，内存占用低
