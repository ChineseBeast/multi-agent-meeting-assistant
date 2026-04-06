package agent

import (
	"fmt"
	"log"

	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/model"
)

// FollowUpAgent 跟进Agent - Go版
// Pipeline 最后一个节点，汇聚所有并行结果
type FollowUpAgent struct{}

func NewFollowUpAgent() *FollowUpAgent {
	return &FollowUpAgent{}
}

// Process 执行会后跟进
func (a *FollowUpAgent) Process(state *model.MeetingState) *model.MeetingState {
	log.Printf("[FollowUpAgent] Processing meeting: %s", state.MeetingID)

	result := &model.FollowUpResult{
		MeetingID:   state.MeetingID,
		SummarySent: true,
		ReportURL:   fmt.Sprintf("/reports/%s.md", state.MeetingID),
	}

	if state.Summary != nil {
		result.Recipients = state.Summary.Participants
	}

	// 统计 Jira 同步结果
	for _, item := range state.ActionItems {
		if item.JiraIssueKey != "" {
			result.JiraIssuesCreated = append(result.JiraIssuesCreated, item.JiraIssueKey)
		}
		if item.FeishuTaskID != "" {
			result.FeishuTasksCreated = append(result.FeishuTasksCreated, item.FeishuTaskID)
		}
		if item.Deadline != "" {
			result.RemindersScheduled++
		}
	}

	state.FollowUp = result
	state.Status = "completed"

	log.Printf("[FollowUpAgent] Follow-up complete: reminders=%d", result.RemindersScheduled)
	return state
}
