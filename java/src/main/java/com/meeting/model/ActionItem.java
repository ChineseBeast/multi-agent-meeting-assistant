package com.meeting.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 单条行动项/待办事项
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ActionItem {

    private String id;
    private String assignee;
    private String task;

    @Builder.Default
    private String deadline = "";

    @Builder.Default
    private String priority = "medium";

    @Builder.Default
    private String context = "";

    private String jiraIssueKey;
    private String feishuTaskId;
}
