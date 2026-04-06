package com.meeting.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * LangGraph4j 会议处理状态 —— 在 Graph 的所有节点之间共享。
 *
 * 对应 Python 版的 MeetingState，是整个 Pipeline 的核心数据结构。
 * 每个 Agent（节点）读取自己需要的字段，处理后将结果写入对应字段。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MeetingState {

    private String meetingId;

    @Builder.Default
    private String status = "created";

    private byte[] audioData;

    // Transcription Agent 输出
    @Builder.Default
    private List<TranscriptSegment> transcript = new ArrayList<>();

    @Builder.Default
    private String transcriptText = "";

    // Summary Agent 输出
    private MeetingSummary summary;

    // Action Agent 输出
    @Builder.Default
    private List<ActionItem> actionItems = new ArrayList<>();

    // Insight Agent 输出
    private MeetingInsight insights;

    // Follow-up Agent 输出
    private FollowUpResult followup;

    // 错误记录
    @Builder.Default
    private List<String> errors = new ArrayList<>();

    /**
     * 转换为 Map（LangGraph4j 状态格式）
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("meetingId", meetingId);
        map.put("status", status);
        map.put("audioData", audioData);
        map.put("transcript", transcript);
        map.put("transcriptText", transcriptText);
        map.put("summary", summary);
        map.put("actionItems", actionItems);
        map.put("insights", insights);
        map.put("followup", followup);
        map.put("errors", errors);
        return map;
    }
}
