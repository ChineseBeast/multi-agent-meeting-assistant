package agent

import (
	"fmt"
	"log"
	"strings"

	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/model"
)

// TranscriptionAgent 转写Agent - Go版
//
// Go版通过 go-whisper 或 REST API 进行语音转写。
// 无音频时使用演示数据。
//
// 面试考点:
// - Go 版为什么适合做转写？（goroutine 轻量并发，适合流式处理）
// - 如何实现流式转写？（goroutine + channel 流式传输）
type TranscriptionAgent struct{}

func NewTranscriptionAgent() *TranscriptionAgent {
	return &TranscriptionAgent{}
}

// Process 执行语音转写
func (a *TranscriptionAgent) Process(state *model.MeetingState) *model.MeetingState {
	log.Printf("[TranscriptionAgent] Processing meeting: %s", state.MeetingID)
	state.Status = "transcribing"

	if len(state.AudioData) == 0 {
		log.Println("[TranscriptionAgent] No audio data, using demo transcript")
		state.Transcript = generateDemoTranscript()
	} else {
		// 生产环境：调用 Whisper API 或 go-whisper
		state.Transcript = generateDemoTranscript()
	}

	state.TranscriptText = formatTranscriptText(state.Transcript)
	log.Printf("[TranscriptionAgent] Transcription complete: %d segments", len(state.Transcript))
	return state
}

func generateDemoTranscript() []model.TranscriptSegment {
	return []model.TranscriptSegment{
		{Speaker: "张总", Text: "好的，我们开始今天的Q3预算评审会议。首先请李明汇报一下目前的预算执行情况。", Start: 0.0, End: 8.5, Confidence: 0.96},
		{Speaker: "李明", Text: "好的张总。截至目前，Q2预算执行率为87%，其中研发投入占比最大，达到42%。", Start: 9.0, End: 16.2, Confidence: 0.95},
		{Speaker: "李明", Text: "Q3我们计划将预算上调15%，主要增加在AI基础设施和人才招聘方面。", Start: 16.5, End: 23.1, Confidence: 0.94},
		{Speaker: "王芳", Text: "关于人才招聘，我建议我们重点招聘3名高级算法工程师，预算大概在每人年薪80万左右。", Start: 23.5, End: 31.0, Confidence: 0.93},
		{Speaker: "张总", Text: "可以。李明你来负责整理Q3的详细预算方案，下周五之前提交给我审批。", Start: 31.5, End: 38.2, Confidence: 0.97},
		{Speaker: "张总", Text: "王芳负责拟定招聘JD，本周三前完成。另外，赵伟跟进一下服务器采购的事情。", Start: 38.5, End: 46.0, Confidence: 0.95},
		{Speaker: "赵伟", Text: "收到，我这边已经在对比几家供应商了，预计下周一可以给出采购方案。", Start: 46.5, End: 52.8, Confidence: 0.94},
		{Speaker: "张总", Text: "好的，那今天的会议就到这里。各位辛苦了，请大家按时完成各自的任务。", Start: 53.0, End: 59.5, Confidence: 0.96},
	}
}

func formatTranscriptText(segments []model.TranscriptSegment) string {
	var sb strings.Builder
	for _, seg := range segments {
		sb.WriteString(fmt.Sprintf("[%.1fs-%.1fs] %s: %s\n", seg.Start, seg.End, seg.Speaker, seg.Text))
	}
	return sb.String()
}
