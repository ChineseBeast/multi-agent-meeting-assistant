package com.meeting.agent;

import com.meeting.model.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Follow-up Agent（跟进Agent）- Java版
 *
 * 汇聚 Summary + Action + Insight 结果，执行会后跟进。
 * 这是 Pipeline 的最后一个节点（Fan-in 汇聚点）。
 */
@Component
public class FollowUpAgent {

    private static final Logger log = LoggerFactory.getLogger(FollowUpAgent.class);

    public MeetingState process(MeetingState state) {
        log.info("[FollowUpAgent] Processing meeting: {}", state.getMeetingId());

        MeetingSummary summary = state.getSummary();
        List<ActionItem> actions = state.getActionItems();
        MeetingInsight insights = state.getInsights();

        FollowUpResult.FollowUpResultBuilder builder = FollowUpResult.builder()
                .meetingId(state.getMeetingId());

        // 统计 Jira 同步结果
        if (actions != null) {
            List<String> jiraKeys = actions.stream()
                    .map(ActionItem::getJiraIssueKey)
                    .filter(k -> k != null && !k.isEmpty())
                    .collect(Collectors.toList());
            builder.jiraIssuesCreated(jiraKeys);

            List<String> feishuIds = actions.stream()
                    .map(ActionItem::getFeishuTaskId)
                    .filter(id -> id != null && !id.isEmpty())
                    .collect(Collectors.toList());
            builder.feishuTasksCreated(feishuIds);

            int reminders = (int) actions.stream()
                    .filter(a -> a.getDeadline() != null && !a.getDeadline().isEmpty())
                    .count();
            builder.remindersScheduled(reminders);
        }

        if (summary != null) {
            builder.recipients(summary.getParticipants());
        }

        builder.summarySent(true);
        builder.reportUrl("/reports/" + state.getMeetingId() + ".md");

        state.setFollowup(builder.build());
        state.setStatus("completed");

        log.info("[FollowUpAgent] Follow-up complete for meeting: {}",
                state.getMeetingId());
        return state;
    }
}
