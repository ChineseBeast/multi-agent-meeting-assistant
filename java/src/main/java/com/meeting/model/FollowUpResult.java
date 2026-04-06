package com.meeting.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 跟进执行结果
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FollowUpResult {

    private String meetingId;

    @Builder.Default
    private boolean summarySent = false;

    @Builder.Default
    private List<String> recipients = new ArrayList<>();

    @Builder.Default
    private List<String> jiraIssuesCreated = new ArrayList<>();

    @Builder.Default
    private List<String> feishuTasksCreated = new ArrayList<>();

    @Builder.Default
    private int remindersScheduled = 0;

    @Builder.Default
    private String reportUrl = "";
}
