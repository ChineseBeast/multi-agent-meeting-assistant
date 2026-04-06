package com.meeting;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * 多Agent智能会议助手系统 - Java版 入口
 *
 * 技术栈: Spring Boot 3 + LangGraph4j + WebSocket
 * 编排模式: Pipeline + 并行 (Fan-out/Fan-in)
 */
@SpringBootApplication
@EnableAsync
public class MeetingApplication {

    public static void main(String[] args) {
        SpringApplication.run(MeetingApplication.class, args);
    }
}
