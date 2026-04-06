package agent

import (
	"log"

	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/model"
)

// SummaryAgent 摘要Agent - Go版
// 与 ActionAgent、InsightAgent 通过 goroutine 并行执行
type SummaryAgent struct{}

func NewSummaryAgent() *SummaryAgent {
	return &SummaryAgent{}
}

// Process 生成结构化会议纪要
func (a *SummaryAgent) Process(state *model.MeetingState) *model.MeetingState {
	log.Printf("[SummaryAgent] Processing meeting: %s", state.MeetingID)

	if state.TranscriptText == "" {
		state.Summary = &model.MeetingSummary{Title: "未知会议"}
		return state
	}

	// 生产环境：调用 LLM API 生成摘要
	// 此处使用演示数据
	state.Summary = &model.MeetingSummary{
		Title:        "Q3预算评审会议",
		Date:         "2026-04-06",
		Participants: []string{"张总", "李明", "王芳", "赵伟"},
		Topics: []model.TopicSummary{
			{
				Title:            "Q2预算执行情况",
				DiscussionPoints: []string{"Q2执行率87%", "研发投入占比42%"},
				Participants:     []string{"李明"},
				Conclusion:       "执行情况良好",
			},
			{
				Title:            "Q3预算调整",
				DiscussionPoints: []string{"预算上调15%", "增加AI基础设施投入", "增加人才招聘预算"},
				Participants:     []string{"李明", "王芳"},
				Conclusion:       "同意上调15%",
			},
			{
				Title:            "人才招聘计划",
				DiscussionPoints: []string{"招聘3名高级算法工程师", "年薪预算80万/人"},
				Participants:     []string{"王芳"},
				Conclusion:       "王芳负责JD拟定",
			},
			{
				Title:            "服务器采购",
				DiscussionPoints: []string{"正在对比供应商"},
				Participants:     []string{"赵伟"},
				Conclusion:       "下周一出采购方案",
			},
		},
		Decisions: []string{"Q3预算上调15%", "招聘3名高级算法工程师"},
		NextSteps: []string{
			"李明下周五提交预算方案",
			"王芳本周三完成招聘JD",
			"赵伟下周一出服务器采购方案",
		},
	}

	log.Printf("[SummaryAgent] Summary generated: %s", state.Summary.Title)
	return state
}
