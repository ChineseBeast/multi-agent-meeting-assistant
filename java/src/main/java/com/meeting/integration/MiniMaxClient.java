package com.meeting.integration;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

/**
 * MiniMax LLM 客户端 - Java版
 *
 * 支持 MiniMax M2.7 模型，兼容 OpenAI 接口格式。
 */
@Component
public class MiniMaxClient {

    private static final Logger log = LoggerFactory.getLogger(MiniMaxClient.class);
    private static final String BASE_URL = "https://api.minimax.chat/v1";
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final OkHttpClient httpClient;

    @Value("${minimax.api-key:}")
    private String apiKey;

    @Value("${minimax.group-id:}")
    private String groupId;

    @Value("${minimax.model:abab6.5s-chat}")
    private String model;

    public MiniMaxClient() {
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                .build();
    }

    public String chat(String userMessage) throws IOException {
        if (apiKey == null || apiKey.isEmpty()) {
            log.warn("MiniMax API key not configured, returning mock response");
            return getMockResponse(userMessage);
        }

        String jsonBody = objectMapper.writeValueAsString(new java.util.HashMap<>() {{
            put("model", model);
            put("messages", new Object[]{
                    new java.util.HashMap<>() {{
                        put("role", "user");
                        put("content", userMessage);
                    }}
            });
            put("temperature", 0.3);
            put("max_tokens", 4096);
            put("response_format", new java.util.HashMap<>() {{
                put("type", "json_object");
            }});
        }});

        String url = BASE_URL + "/text/chatcompletion_v2";
        if (groupId != null && !groupId.isEmpty()) {
            url += "?GroupId=" + groupId;
        }

        Request request = new Request.Builder()
                .url(url)
                .addHeader("Authorization", "Bearer " + apiKey)
                .addHeader("Content-Type", "application/json")
                .post(RequestBody.create(jsonBody, MediaType.parse("application/json")))
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            String body = response.body() != null ? response.body().string() : "";
            JsonNode root = objectMapper.readTree(body);

            if (root.has("choices") && root.get("choices").size() > 0) {
                return root.get("choices").get(0).path("message").path("content").asText();
            }
            throw new IOException("Unexpected MiniMax API response: " + body);
        }
    }

    private String getMockResponse(String prompt) {
        if (prompt.contains("纪要") || prompt.contains("summary")) {
            return """
                {"title":"Q3预算评审会议","date":"2026-04-06","participants":["张总","李明","王芳","赵伟"],
                "topics":[{"title":"Q2预算执行情况","discussionPoints":["Q2执行率87%","研发投入42%"],"participants":["李明"],"conclusion":"执行情况良好"},
                {"title":"Q3预算调整","discussionPoints":["预算上调15%","AI基础设施投入","人才招聘"],"participants":["李明","王芳"],"conclusion":"同意上调"},
                {"title":"人才招聘","discussionPoints":["招聘3名高级算法工程师","年薪80万/人"],"participants":["王芳"],"conclusion":"王芳负责JD"},
                {"title":"服务器采购","discussionPoints":["对比供应商中"],"participants":["赵伟"],"conclusion":"下周一出方案"}],
                "decisions":["Q3预算上调15%","招聘3名高级算法工程师"],
                "nextSteps":["李明下周五提交预算方案","王芳本周三完成JD","赵伟下周一出采购方案"]}""";
        }
        return """
            {"action_items":[
            {"assignee":"李明","task":"整理Q3详细预算方案","deadline":"2026-04-11","priority":"high","context":"张总要求Q3预算上调15%"},
            {"assignee":"王芳","task":"拟定高级算法工程师招聘JD","deadline":"2026-04-08","priority":"high","context":"计划招聘3名高级算法工程师"},
            {"assignee":"赵伟","task":"完成服务器采购方案","deadline":"2026-04-07","priority":"medium","context":"正在对比供应商"}]}""";
    }
}
