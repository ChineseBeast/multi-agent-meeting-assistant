package model

// TranscriptSegment 单条转写片段
type TranscriptSegment struct {
	Speaker    string  `json:"speaker"`
	Text       string  `json:"text"`
	Start      float64 `json:"start"`
	End        float64 `json:"end"`
	Confidence float64 `json:"confidence"`
}

// MeetingSummary 结构化会议纪要
type MeetingSummary struct {
	Title        string         `json:"title"`
	Date         string         `json:"date"`
	Participants []string       `json:"participants"`
	Topics       []TopicSummary `json:"topics"`
	Decisions    []string       `json:"decisions"`
	NextSteps    []string       `json:"next_steps"`
}

// TopicSummary 单个议题摘要
type TopicSummary struct {
	Title            string   `json:"title"`
	DiscussionPoints []string `json:"discussion_points"`
	Participants     []string `json:"participants"`
	Conclusion       string   `json:"conclusion"`
}

// ActionItem 单条行动项
type ActionItem struct {
	ID            string `json:"id"`
	Assignee      string `json:"assignee"`
	Task          string `json:"task"`
	Deadline      string `json:"deadline"`
	Priority      string `json:"priority"`
	Context       string `json:"context"`
	JiraIssueKey  string `json:"jira_issue_key,omitempty"`
	FeishuTaskID  string `json:"feishu_task_id,omitempty"`
}

// SpeakerStats 说话人统计
type SpeakerStats struct {
	Speaker          string  `json:"speaker"`
	SpeakingDuration float64 `json:"speaking_duration"`
	SpeakingRatio    float64 `json:"speaking_ratio"`
	WordCount        int     `json:"word_count"`
	SegmentCount     int     `json:"segment_count"`
}

// MeetingInsight 会议洞察
type MeetingInsight struct {
	MeetingID        string         `json:"meeting_id"`
	OverallSentiment string         `json:"overall_sentiment"`
	SentimentScore   float64        `json:"sentiment_score"`
	SpeakerStats     []SpeakerStats `json:"speaker_stats"`
	EfficiencyScore  float64        `json:"efficiency_score"`
	Keywords         []string       `json:"keywords"`
	Highlights       []string       `json:"highlights"`
	Suggestions      []string       `json:"suggestions"`
}

// FollowUpResult 跟进结果
type FollowUpResult struct {
	MeetingID          string   `json:"meeting_id"`
	SummarySent        bool     `json:"summary_sent"`
	Recipients         []string `json:"recipients"`
	JiraIssuesCreated  []string `json:"jira_issues_created"`
	FeishuTasksCreated []string `json:"feishu_tasks_created"`
	RemindersScheduled int      `json:"reminders_scheduled"`
	ReportURL          string   `json:"report_url"`
}

// MeetingState LangGraph 风格的会议处理状态
// 在 Go 版中，使用 goroutine + channel 实现并行编排
type MeetingState struct {
	MeetingID      string              `json:"meeting_id"`
	Status         string              `json:"status"`
	AudioData      []byte              `json:"-"`
	Transcript     []TranscriptSegment `json:"transcript"`
	TranscriptText string              `json:"transcript_text"`
	Summary        *MeetingSummary     `json:"summary"`
	ActionItems    []ActionItem        `json:"action_items"`
	Insights       *MeetingInsight     `json:"insights"`
	FollowUp       *FollowUpResult     `json:"followup"`
	Errors         []string            `json:"errors"`
}
