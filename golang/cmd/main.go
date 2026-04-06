package main

import (
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/graph"
	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/model"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

var (
	pipeline       = graph.NewMeetingPipeline()
	meetingResults = make(map[string]*model.MeetingState)
	resultsMu      sync.RWMutex
	upgrader       = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}
)

func main() {
	port := os.Getenv("SERVER_PORT")
	if port == "" {
		port = "8090"
	}

	r := gin.Default()

	// REST API 路由
	r.GET("/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"name":    "多Agent智能会议助手 (Go版)",
			"version": "1.0.0",
			"docs":    "/api/v1/meeting/start",
		})
	})

	api := r.Group("/api/v1")
	{
		api.POST("/meeting/start", startMeeting)
		api.POST("/meeting/:id/demo", runDemo)
		api.GET("/meeting/:id/summary", getSummary)
		api.GET("/meeting/:id/actions", getActions)
		api.GET("/meeting/:id/insights", getInsights)
		api.GET("/meeting/:id/report", getReport)
	}

	// WebSocket 路由
	r.GET("/ws/meeting/:id", handleWebSocket)

	log.Printf("Starting Go Meeting Assistant on :%s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func startMeeting(c *gin.Context) {
	meetingID := "go-" + c.Query("id")
	if meetingID == "go-" {
		meetingID = "go-demo"
	}
	c.JSON(200, gin.H{
		"meeting_id":    meetingID,
		"websocket_url": "ws://localhost:8090/ws/meeting/" + meetingID,
		"status":        "created",
	})
}

func runDemo(c *gin.Context) {
	meetingID := c.Param("id")

	state := &model.MeetingState{
		MeetingID: meetingID,
		Status:    "created",
	}

	result := pipeline.Execute(state)

	resultsMu.Lock()
	meetingResults[meetingID] = result
	resultsMu.Unlock()

	c.JSON(200, result)
}

func getSummary(c *gin.Context) {
	resultsMu.RLock()
	result, ok := meetingResults[c.Param("id")]
	resultsMu.RUnlock()
	if !ok {
		c.JSON(404, gin.H{"error": "Meeting not found"})
		return
	}
	c.JSON(200, result.Summary)
}

func getActions(c *gin.Context) {
	resultsMu.RLock()
	result, ok := meetingResults[c.Param("id")]
	resultsMu.RUnlock()
	if !ok {
		c.JSON(404, gin.H{"error": "Meeting not found"})
		return
	}
	c.JSON(200, result.ActionItems)
}

func getInsights(c *gin.Context) {
	resultsMu.RLock()
	result, ok := meetingResults[c.Param("id")]
	resultsMu.RUnlock()
	if !ok {
		c.JSON(404, gin.H{"error": "Meeting not found"})
		return
	}
	c.JSON(200, result.Insights)
}

func getReport(c *gin.Context) {
	resultsMu.RLock()
	result, ok := meetingResults[c.Param("id")]
	resultsMu.RUnlock()
	if !ok {
		c.JSON(404, gin.H{"error": "Meeting not found"})
		return
	}
	c.JSON(200, result)
}

func handleWebSocket(c *gin.Context) {
	meetingID := c.Param("id")
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}
	defer conn.Close()

	log.Printf("WebSocket connected: %s", meetingID)
	conn.WriteJSON(gin.H{"type": "connected", "meeting_id": meetingID})

	for {
		_, msg, err := conn.ReadMessage()
		if err != nil {
			log.Printf("WebSocket read error: %v", err)
			break
		}

		if string(msg) == `{"type":"demo"}` {
			conn.WriteJSON(gin.H{"type": "processing", "message": "运行演示模式..."})

			state := &model.MeetingState{MeetingID: meetingID, Status: "created"}
			result := pipeline.Execute(state)

			conn.WriteJSON(gin.H{"type": "result", "data": result})
			conn.WriteJSON(gin.H{"type": "completed", "meeting_id": meetingID})
		}
	}
}
