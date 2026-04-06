package com.meeting.agent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.meeting.integration.JiraIntegration;
import com.meeting.integration.MiniMaxClient;
import com.meeting.model.ActionItem;
import com.meeting.model.MeetingState;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Action Agent（待办Agent）- Java版
 *
 * 提取行动项并同步到 Jira/飞书。
 * 与 Summary Agent、Insight Agent 并行执行。
 *
 * 面试考点:
 * - 如何保证 Jira 同步的幂等性？
 * - CompletableFuture 并行同步 Jira 和飞书
 */
@Component
public class ActionAgent {

    private static final Logger log = LoggerFactory.getLogger(ActionAgent.class);
    private final MiniMaxClient llmClient;
    private final JiraIntegration jiraIntegration;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ActionAgent(MiniMaxClient llmClient, JiraIntegration jiraIntegration) {
        this.llmClient = llmClient;
        this.jiraIntegration = jiraIntegration;
    }

    public MeetingState process(MeetingState state) {
        log.info("[ActionAgent] Processing meeting: {}", state.getMeetingId());

        String transcriptText = state.getTranscriptText();
        if (transcriptText == null || transcriptText.isEmpty()) {
            state.setActionItems(List.of());
            return state;
        }

        try {
            String prompt = buildPrompt(transcriptText);
            String response = llmClient.chat(prompt);
            List<ActionItem> items = parseResponse(response);

            // 同步到 Jira
            for (ActionItem item : items) {
                try {
                    String issueKey = jiraIntegration.createIssue(
                            item.getTask(), item.getAssignee(),
                            item.getDeadline(), item.getPriority());
                    item.setJiraIssueKey(issueKey);
                } catch (Exception e) {
                    log.warn("Failed to sync to Jira: {}", e.getMessage());
                }
            }

            state.setActionItems(items);
            log.info("[ActionAgent] Extracted {} action items", items.size());
        } catch (Exception e) {
            log.error("[ActionAgent] Error: {}", e.getMessage());
            state.getErrors().add("ActionAgent: " + e.getMessage());
            state.setActionItems(List.of());
        }

        return state;
    }

    private String buildPrompt(String transcript) {
        return """
            你是专业的任务提取助手。请从会议转写文本中提取所有行动项。
            今天日期: %s
            严格JSON输出:
            {"action_items": [{"assignee": "人", "task": "任务", "deadline": "YYYY-MM-DD", "priority": "low/medium/high/urgent", "context": "背景"}]}

            会议转写文本：
            """.formatted(LocalDate.now()) + transcript;
    }

    private List<ActionItem> parseResponse(String response) {
        List<ActionItem> items = new ArrayList<>();
        try {
            JsonNode root = objectMapper.readTree(response);
            JsonNode itemsNode = root.path("action_items");
            if (itemsNode.isArray()) {
                for (JsonNode node : itemsNode) {
                    items.add(ActionItem.builder()
                            .id(UUID.randomUUID().toString().substring(0, 8))
                            .assignee(node.path("assignee").asText("未指定"))
                            .task(node.path("task").asText(""))
                            .deadline(node.path("deadline").asText(""))
                            .priority(node.path("priority").asText("medium"))
                            .context(node.path("context").asText(""))
                            .build());
                }
            }
        } catch (Exception e) {
            log.error("Failed to parse action items: {}", e.getMessage());
        }
        return items;
    }
}
