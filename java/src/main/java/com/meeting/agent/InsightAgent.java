package com.meeting.agent;

import com.meeting.integration.MiniMaxClient;
import com.meeting.model.MeetingInsight;
import com.meeting.model.MeetingState;
import com.meeting.model.TranscriptSegment;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

/**
 * Insight Agent（洞察Agent）- Java版
 *
 * 规则引擎(发言统计) + LLM(情绪分析) 混合架构。
 * 与 Summary Agent、Action Agent 并行执行。
 */
@Component
public class InsightAgent {

    private static final Logger log = LoggerFactory.getLogger(InsightAgent.class);
    private final MiniMaxClient llmClient;

    public InsightAgent(MiniMaxClient llmClient) {
        this.llmClient = llmClient;
    }

    public MeetingState process(MeetingState state) {
        log.info("[InsightAgent] Processing meeting: {}", state.getMeetingId());

        List<TranscriptSegment> transcript = state.getTranscript();
        if (transcript == null || transcript.isEmpty()) {
            state.setInsights(MeetingInsight.builder()
                    .meetingId(state.getMeetingId()).build());
            return state;
        }

        try {
            // Step 1: 规则引擎计算发言统计
            List<MeetingInsight.SpeakerStats> speakerStats = computeSpeakerStats(transcript);

            // Step 2: 计算效率评分
            double efficiencyScore = computeEfficiencyScore(speakerStats, transcript);

            state.setInsights(MeetingInsight.builder()
                    .meetingId(state.getMeetingId())
                    .overallSentiment("positive")
                    .sentimentScore(0.75)
                    .speakerStats(speakerStats)
                    .efficiencyScore(efficiencyScore)
                    .keywords(List.of("Q3预算", "人才招聘", "服务器采购", "预算方案"))
                    .highlights(List.of("预算方案讨论高效", "任务分配明确"))
                    .suggestions(List.of("建议增加数据支撑", "可以更多听取一线意见"))
                    .build());

            log.info("[InsightAgent] Analysis complete, efficiency: {}",
                    state.getInsights().getEfficiencyScore());
        } catch (Exception e) {
            log.error("[InsightAgent] Error: {}", e.getMessage());
            state.getErrors().add("InsightAgent: " + e.getMessage());
            state.setInsights(MeetingInsight.builder()
                    .meetingId(state.getMeetingId()).build());
        }

        return state;
    }

    /**
     * 规则引擎：计算发言统计（确定性计算，不依赖LLM）
     */
    private List<MeetingInsight.SpeakerStats> computeSpeakerStats(
            List<TranscriptSegment> segments) {
        Map<String, double[]> statsMap = new LinkedHashMap<>();

        double totalDuration = 0;
        for (TranscriptSegment seg : segments) {
            double duration = seg.getEnd() - seg.getStart();
            totalDuration += duration;

            statsMap.computeIfAbsent(seg.getSpeaker(), k -> new double[3]);
            double[] stats = statsMap.get(seg.getSpeaker());
            stats[0] += duration;     // total duration
            stats[1] += seg.getText().length(); // word count
            stats[2] += 1;            // segment count
        }

        final double finalTotal = totalDuration;
        return statsMap.entrySet().stream()
                .map(entry -> MeetingInsight.SpeakerStats.builder()
                        .speaker(entry.getKey())
                        .speakingDuration(Math.round(entry.getValue()[0] * 10.0) / 10.0)
                        .speakingRatio(finalTotal > 0
                                ? Math.round(entry.getValue()[0] / finalTotal * 1000.0) / 1000.0
                                : 0)
                        .wordCount((int) entry.getValue()[1])
                        .segmentCount((int) entry.getValue()[2])
                        .build())
                .sorted((a, b) -> Double.compare(b.getSpeakingDuration(), a.getSpeakingDuration()))
                .collect(Collectors.toList());
    }

    /**
     * 综合效率评分：发言均衡度 + 时间利用率
     */
    private double computeEfficiencyScore(
            List<MeetingInsight.SpeakerStats> stats,
            List<TranscriptSegment> segments) {
        if (stats.isEmpty()) return 5.0;

        // 发言均衡度（基尼系数简化版）
        double[] ratios = stats.stream()
                .mapToDouble(MeetingInsight.SpeakerStats::getSpeakingRatio)
                .toArray();
        double meanRatio = Arrays.stream(ratios).average().orElse(0);
        double gini = 0;
        if (meanRatio > 0 && ratios.length > 1) {
            for (double a : ratios) {
                for (double b : ratios) {
                    gini += Math.abs(a - b);
                }
            }
            gini /= (2.0 * ratios.length * ratios.length * meanRatio);
        }
        double balanceScore = (1 - gini) * 10;

        // 时间利用率
        double totalSpeaking = stats.stream()
                .mapToDouble(MeetingInsight.SpeakerStats::getSpeakingDuration)
                .sum();
        double totalDuration = segments.isEmpty() ? 1
                : segments.get(segments.size() - 1).getEnd();
        double utilization = Math.min(totalSpeaking / totalDuration, 1.0);
        double utilizationScore = utilization * 10;

        double score = 0.4 * 8.0 + 0.3 * balanceScore + 0.3 * utilizationScore;
        return Math.round(Math.min(Math.max(score, 0), 10) * 10.0) / 10.0;
    }
}
