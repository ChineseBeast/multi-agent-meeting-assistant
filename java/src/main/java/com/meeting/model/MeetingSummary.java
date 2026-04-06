package com.meeting.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 结构化会议纪要
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MeetingSummary {

    private String title;
    private String date;

    @Builder.Default
    private List<String> participants = new ArrayList<>();

    @Builder.Default
    private List<TopicSummary> topics = new ArrayList<>();

    @Builder.Default
    private List<String> decisions = new ArrayList<>();

    @Builder.Default
    private List<String> nextSteps = new ArrayList<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TopicSummary {
        private String title;

        @Builder.Default
        private List<String> discussionPoints = new ArrayList<>();

        @Builder.Default
        private List<String> participants = new ArrayList<>();

        private String conclusion;
    }
}
