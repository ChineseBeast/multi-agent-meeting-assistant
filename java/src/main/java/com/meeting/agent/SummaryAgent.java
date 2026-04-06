package com.meeting.agent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.meeting.integration.MiniMaxClient;
import com.meeting.model.MeetingState;
import com.meeting.model.MeetingSummary;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * Summary Agent（摘要Agent）- Java版
 *
 * 使用 LLM 生成结构化会议纪要。
 * 与 Action Agent、Insight Agent 并行执行。
 */
@Component
public class SummaryAgent {

    private static final Logger log = LoggerFactory.getLogger(SummaryAgent.class);
    private final MiniMaxClient llmClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public SummaryAgent(MiniMaxClient llmClient) {
        this.llmClient = llmClient;
    }

    public MeetingState process(MeetingState state) {
        log.info("[SummaryAgent] Processing meeting: {}", state.getMeetingId());

        String transcriptText = state.getTranscriptText();
        if (transcriptText == null || transcriptText.isEmpty()) {
            state.setSummary(MeetingSummary.builder().title("未知会议").build());
            return state;
        }

        try {
            String prompt = buildPrompt(transcriptText);
            String response = llmClient.chat(prompt);
            MeetingSummary summary = parseResponse(response);
            state.setSummary(summary);
            log.info("[SummaryAgent] Summary generated: {}", summary.getTitle());
        } catch (Exception e) {
            log.error("[SummaryAgent] Error: {}", e.getMessage());
            state.getErrors().add("SummaryAgent: " + e.getMessage());
            state.setSummary(MeetingSummary.builder()
                    .title("会议纪要（降级模式）").build());
        }

        return state;
    }

    private String buildPrompt(String transcript) {
        return """
            你是专业的会议纪要助手。请根据以下会议转写文本生成结构化的会议纪要。
            严格按照JSON格式输出：
            {
              "title": "会议主题",
              "date": "会议日期",
              "participants": ["参会人"],
              "topics": [{"title": "议题", "discussionPoints": ["要点"], "participants": ["人"], "conclusion": "结论"}],
              "decisions": ["决策"],
              "nextSteps": ["下一步"]
            }

            会议转写文本：
            """ + transcript;
    }

    private MeetingSummary parseResponse(String response) {
        try {
            JsonNode root = objectMapper.readTree(response);

            List<MeetingSummary.TopicSummary> topics = new ArrayList<>();
            if (root.has("topics")) {
                for (JsonNode topicNode : root.get("topics")) {
                    topics.add(MeetingSummary.TopicSummary.builder()
                            .title(topicNode.path("title").asText(""))
                            .discussionPoints(jsonArrayToList(topicNode.path("discussionPoints")))
                            .participants(jsonArrayToList(topicNode.path("participants")))
                            .conclusion(topicNode.path("conclusion").asText(""))
                            .build());
                }
            }

            return MeetingSummary.builder()
                    .title(root.path("title").asText("会议纪要"))
                    .date(root.path("date").asText(""))
                    .participants(jsonArrayToList(root.path("participants")))
                    .topics(topics)
                    .decisions(jsonArrayToList(root.path("decisions")))
                    .nextSteps(jsonArrayToList(root.path("nextSteps")))
                    .build();
        } catch (Exception e) {
            log.error("Failed to parse summary response: {}", e.getMessage());
            return MeetingSummary.builder().title("解析失败").build();
        }
    }

    private List<String> jsonArrayToList(JsonNode node) {
        List<String> list = new ArrayList<>();
        if (node != null && node.isArray()) {
            node.forEach(n -> list.add(n.asText()));
        }
        return list;
    }
}
