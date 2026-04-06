package graph

import (
	"log"
	"sync"

	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/agent"
	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/model"
)

// MeetingPipeline 会议处理管道 - Go版编排核心
//
// Go 天然适合并行编排：goroutine + channel + sync.WaitGroup
//
// 编排模式: Pipeline + 并行 (Fan-out / Fan-in)
//
//	                  ┌─────────────┐
//	                  │ Transcription│  ← goroutine (串行)
//	                  └──────┬───────┘
//	                         │
//	                  ┌──────┼───────┐  ← goroutine fan-out
//	                  │      │       │
//	                  ▼      ▼       ▼
//	               Summary Action Insight  ← 三个 goroutine 并行
//	                  │      │       │
//	                  └──────┼───────┘  ← sync.WaitGroup fan-in
//	                         │
//	                  ┌──────────────┐
//	                  │  Follow-up   │  ← goroutine (串行)
//	                  └──────────────┘
//
// 面试考点:
// - Go 的 goroutine 和 Java 的 CompletableFuture 有什么区别？
// - channel 在这里起什么作用？（传递并行结果）
// - sync.WaitGroup 的作用？（等待所有并行 goroutine 完成）
type MeetingPipeline struct {
	transcription *agent.TranscriptionAgent
	summary       *agent.SummaryAgent
	action        *agent.ActionAgent
	insight       *agent.InsightAgent
	followup      *agent.FollowUpAgent
}

// NewMeetingPipeline 创建会议处理管道
func NewMeetingPipeline() *MeetingPipeline {
	return &MeetingPipeline{
		transcription: agent.NewTranscriptionAgent(),
		summary:       agent.NewSummaryAgent(),
		action:        agent.NewActionAgent(),
		insight:       agent.NewInsightAgent(),
		followup:      agent.NewFollowUpAgent(),
	}
}

// Execute 执行完整的会议处理 Pipeline
func (p *MeetingPipeline) Execute(state *model.MeetingState) *model.MeetingState {
	log.Printf("Starting meeting pipeline: %s", state.MeetingID)

	// ============ Pipeline Stage 1: Transcription (串行) ============
	state = p.transcription.Process(state)
	log.Println("Transcription complete, starting parallel processing...")

	// ============ Fan-out Stage: 并行执行 (goroutine) ============
	var wg sync.WaitGroup
	var mu sync.Mutex

	// 为并行 Agent 创建独立的状态副本
	summaryState := copyState(state)
	actionState := copyState(state)
	insightState := copyState(state)

	wg.Add(3)

	// Summary Agent goroutine
	go func() {
		defer wg.Done()
		result := p.summary.Process(summaryState)
		mu.Lock()
		state.Summary = result.Summary
		state.Errors = append(state.Errors, result.Errors...)
		mu.Unlock()
	}()

	// Action Agent goroutine
	go func() {
		defer wg.Done()
		result := p.action.Process(actionState)
		mu.Lock()
		state.ActionItems = result.ActionItems
		state.Errors = append(state.Errors, result.Errors...)
		mu.Unlock()
	}()

	// Insight Agent goroutine
	go func() {
		defer wg.Done()
		result := p.insight.Process(insightState)
		mu.Lock()
		state.Insights = result.Insights
		state.Errors = append(state.Errors, result.Errors...)
		mu.Unlock()
	}()

	// ============ Fan-in: 等待所有并行 Agent 完成 ============
	wg.Wait()
	log.Println("Parallel processing complete, starting follow-up...")

	// ============ Pipeline Stage 3: Follow-up (串行) ============
	state = p.followup.Process(state)

	log.Printf("Meeting pipeline completed: %s", state.MeetingID)
	return state
}

func copyState(original *model.MeetingState) *model.MeetingState {
	errors := make([]string, len(original.Errors))
	copy(errors, original.Errors)

	transcript := make([]model.TranscriptSegment, len(original.Transcript))
	copy(transcript, original.Transcript)

	return &model.MeetingState{
		MeetingID:      original.MeetingID,
		Status:         original.Status,
		Transcript:     transcript,
		TranscriptText: original.TranscriptText,
		Errors:         errors,
	}
}
