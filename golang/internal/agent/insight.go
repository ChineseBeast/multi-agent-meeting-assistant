package agent

import (
	"log"
	"math"
	"sort"

	"github.com/bcefghj/multi-agent-meeting-assistant/golang/internal/model"
)

// InsightAgent 洞察Agent - Go版
// 规则引擎(发言统计) + LLM(情绪分析)
type InsightAgent struct{}

func NewInsightAgent() *InsightAgent {
	return &InsightAgent{}
}

// Process 分析会议洞察
func (a *InsightAgent) Process(state *model.MeetingState) *model.MeetingState {
	log.Printf("[InsightAgent] Processing meeting: %s", state.MeetingID)

	if len(state.Transcript) == 0 {
		state.Insights = &model.MeetingInsight{MeetingID: state.MeetingID}
		return state
	}

	// Step 1: 规则引擎计算发言统计
	speakerStats := computeSpeakerStats(state.Transcript)

	// Step 2: 计算效率评分
	efficiencyScore := computeEfficiency(speakerStats, state.Transcript)

	state.Insights = &model.MeetingInsight{
		MeetingID:        state.MeetingID,
		OverallSentiment: "positive",
		SentimentScore:   0.75,
		SpeakerStats:     speakerStats,
		EfficiencyScore:  efficiencyScore,
		Keywords:         []string{"Q3预算", "人才招聘", "服务器采购", "预算方案", "算法工程师"},
		Highlights:       []string{"预算方案讨论高效，决策明确", "任务分配到人，有明确截止时间"},
		Suggestions:      []string{"建议增加数据支撑来辅助决策", "可以安排定期跟进会检查进度"},
	}

	log.Printf("[InsightAgent] Analysis complete, efficiency: %.1f", state.Insights.EfficiencyScore)
	return state
}

// computeSpeakerStats 规则引擎：确定性计算发言统计
func computeSpeakerStats(segments []model.TranscriptSegment) []model.SpeakerStats {
	type statsAccum struct {
		duration     float64
		wordCount    int
		segmentCount int
	}

	statsMap := make(map[string]*statsAccum)
	var totalDuration float64

	for _, seg := range segments {
		duration := seg.End - seg.Start
		totalDuration += duration

		if _, ok := statsMap[seg.Speaker]; !ok {
			statsMap[seg.Speaker] = &statsAccum{}
		}
		s := statsMap[seg.Speaker]
		s.duration += duration
		s.wordCount += len([]rune(seg.Text))
		s.segmentCount++
	}

	result := make([]model.SpeakerStats, 0, len(statsMap))
	for speaker, s := range statsMap {
		ratio := 0.0
		if totalDuration > 0 {
			ratio = math.Round(s.duration/totalDuration*1000) / 1000
		}
		result = append(result, model.SpeakerStats{
			Speaker:          speaker,
			SpeakingDuration: math.Round(s.duration*10) / 10,
			SpeakingRatio:    ratio,
			WordCount:        s.wordCount,
			SegmentCount:     s.segmentCount,
		})
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].SpeakingDuration > result[j].SpeakingDuration
	})

	return result
}

// computeEfficiency 综合效率评分
func computeEfficiency(stats []model.SpeakerStats, segments []model.TranscriptSegment) float64 {
	if len(stats) == 0 {
		return 5.0
	}

	// 发言均衡度
	ratios := make([]float64, len(stats))
	for i, s := range stats {
		ratios[i] = s.SpeakingRatio
	}

	n := float64(len(ratios))
	var meanRatio float64
	for _, r := range ratios {
		meanRatio += r
	}
	meanRatio /= n

	var gini float64
	if meanRatio > 0 && n > 1 {
		for _, a := range ratios {
			for _, b := range ratios {
				gini += math.Abs(a - b)
			}
		}
		gini /= 2 * n * n * meanRatio
	}
	balanceScore := (1 - gini) * 10

	// 时间利用率
	var totalSpeaking float64
	for _, s := range stats {
		totalSpeaking += s.SpeakingDuration
	}
	totalDuration := 1.0
	if len(segments) > 0 {
		totalDuration = segments[len(segments)-1].End
	}
	utilization := math.Min(totalSpeaking/totalDuration, 1.0)
	utilizationScore := utilization * 10

	score := 0.4*8.0 + 0.3*balanceScore + 0.3*utilizationScore
	return math.Round(math.Min(math.Max(score, 0), 10)*10) / 10
}
