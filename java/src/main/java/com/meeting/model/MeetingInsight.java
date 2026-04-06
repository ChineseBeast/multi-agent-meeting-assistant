package com.meeting.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 会议洞察分析结果
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MeetingInsight {

    private String meetingId;

    @Builder.Default
    private String overallSentiment = "neutral";

    @Builder.Default
    private double sentimentScore = 0.5;

    @Builder.Default
    private List<SpeakerStats> speakerStats = new ArrayList<>();

    @Builder.Default
    private double efficiencyScore = 0.0;

    @Builder.Default
    private List<String> keywords = new ArrayList<>();

    @Builder.Default
    private List<String> highlights = new ArrayList<>();

    @Builder.Default
    private List<String> suggestions = new ArrayList<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SpeakerStats {
        private String speaker;
        private double speakingDuration;
        private double speakingRatio;
        private int wordCount;
        private int segmentCount;
    }
}
