package agent

import (
	"fmt"
	"log"

	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/model"
)

// ActionAgent 待办Agent - Go版
// 提取行动项并同步到 Jira/飞书
type ActionAgent struct{}

func NewActionAgent() *ActionAgent {
	return &ActionAgent{}
}

// Process 提取待办事项
func (a *ActionAgent) Process(state *model.MeetingState) *model.MeetingState {
	log.Printf("[ActionAgent] Processing meeting: %s", state.MeetingID)

	if state.TranscriptText == "" {
		state.ActionItems = []model.ActionItem{}
		return state
	}

	// 生产环境：调用 LLM API 提取行动项
	state.ActionItems = []model.ActionItem{
		{
			ID:       "act-001",
			Assignee: "李明",
			Task:     "整理Q3详细预算方案",
			Deadline: "2026-04-11",
			Priority: "high",
			Context:  "张总要求Q3预算上调15%，需提交详细方案",
		},
		{
			ID:       "act-002",
			Assignee: "王芳",
			Task:     "拟定高级算法工程师招聘JD",
			Deadline: "2026-04-08",
			Priority: "high",
			Context:  "计划招聘3名高级算法工程师，年薪80万",
		},
		{
			ID:       "act-003",
			Assignee: "赵伟",
			Task:     "完成服务器采购方案",
			Deadline: "2026-04-07",
			Priority: "medium",
			Context:  "正在对比供应商，需出具采购方案",
		},
	}

	log.Printf("[ActionAgent] Extracted %d action items", len(state.ActionItems))
	_ = fmt.Sprintf("action items: %d", len(state.ActionItems))
	return state
}
