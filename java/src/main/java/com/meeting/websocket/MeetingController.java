package com.meeting.websocket;

import com.meeting.graph.MeetingGraph;
import com.meeting.model.MeetingState;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * REST API 控制器 - Java版
 *
 * 提供与 Python 版一致的 REST API 接口。
 */
@RestController
@RequestMapping("/api/v1")
public class MeetingController {

    private final MeetingGraph meetingGraph;
    private final Map<String, MeetingState> meetingResults = new ConcurrentHashMap<>();

    public MeetingController(MeetingGraph meetingGraph) {
        this.meetingGraph = meetingGraph;
    }

    @GetMapping("/")
    public Map<String, String> root() {
        return Map.of(
                "name", "多Agent智能会议助手 (Java版)",
                "version", "1.0.0",
                "docs", "/swagger-ui.html"
        );
    }

    @PostMapping("/meeting/start")
    public Map<String, String> startMeeting() {
        String meetingId = UUID.randomUUID().toString().substring(0, 12);
        return Map.of(
                "meetingId", meetingId,
                "websocketUrl", "ws://localhost:8080/ws/meeting/" + meetingId,
                "status", "created"
        );
    }

    @PostMapping("/meeting/{meetingId}/demo")
    public ResponseEntity<Map<String, Object>> runDemo(@PathVariable String meetingId) {
        MeetingState state = MeetingState.builder()
                .meetingId(meetingId)
                .status("created")
                .build();

        MeetingState result = meetingGraph.execute(state);
        meetingResults.put(meetingId, result);

        Map<String, Object> response = new HashMap<>();
        response.put("meetingId", meetingId);
        response.put("status", result.getStatus());
        response.put("summary", result.getSummary());
        response.put("actionItems", result.getActionItems());
        response.put("insights", result.getInsights());
        response.put("followup", result.getFollowup());
        response.put("errors", result.getErrors());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/meeting/{meetingId}/summary")
    public ResponseEntity<?> getSummary(@PathVariable String meetingId) {
        MeetingState result = meetingResults.get(meetingId);
        if (result == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(result.getSummary());
    }

    @GetMapping("/meeting/{meetingId}/actions")
    public ResponseEntity<?> getActions(@PathVariable String meetingId) {
        MeetingState result = meetingResults.get(meetingId);
        if (result == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(result.getActionItems());
    }

    @GetMapping("/meeting/{meetingId}/insights")
    public ResponseEntity<?> getInsights(@PathVariable String meetingId) {
        MeetingState result = meetingResults.get(meetingId);
        if (result == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(result.getInsights());
    }

    @GetMapping("/meeting/{meetingId}/report")
    public ResponseEntity<?> getReport(@PathVariable String meetingId) {
        MeetingState result = meetingResults.get(meetingId);
        if (result == null) return ResponseEntity.notFound().build();

        Map<String, Object> report = new HashMap<>();
        report.put("meetingId", meetingId);
        report.put("summary", result.getSummary());
        report.put("actionItems", result.getActionItems());
        report.put("insights", result.getInsights());
        report.put("followup", result.getFollowup());
        return ResponseEntity.ok(report);
    }
}
