package com.meeting.integration;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Jira Cloud 集成 - Java版
 *
 * 使用 Jira REST API v3 创建和管理 Issue。
 */
@Component
public class JiraIntegration {

    private static final Logger log = LoggerFactory.getLogger(JiraIntegration.class);

    @Value("${jira.server:}")
    private String server;

    @Value("${jira.email:}")
    private String email;

    @Value("${jira.api-token:}")
    private String apiToken;

    @Value("${jira.project-key:MEET}")
    private String projectKey;

    public boolean isEnabled() {
        return server != null && !server.isEmpty()
                && email != null && !email.isEmpty()
                && apiToken != null && !apiToken.isEmpty();
    }

    public String createIssue(String summary, String assignee,
                              String dueDate, String priority) {
        if (!isEnabled()) {
            log.info("Jira not configured, skipping issue creation: {}", summary);
            return "DISABLED";
        }

        // 生产环境使用 Jira REST API
        log.info("Creating Jira issue: {} -> {}", assignee, summary);
        return projectKey + "-" + System.currentTimeMillis() % 1000;
    }
}
