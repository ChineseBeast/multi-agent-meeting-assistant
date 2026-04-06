package com.meeting.graph;

import com.meeting.agent.*;
import com.meeting.model.MeetingState;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/**
 * LangGraph4j 会议处理图 —— Java版编排核心
 *
 * 编排模式: Pipeline + 并行 (Fan-out / Fan-in)
 *
 * Java 版使用 CompletableFuture 实现并行，等效于 Python LangGraph 的 Fan-out/Fan-in。
 *
 * 面试考点:
 * - Java 中如何实现 Fan-out/Fan-in？（CompletableFuture.allOf）
 * - 与 Python LangGraph 的区别？（Java 显式并发 vs Python 声明式Graph）
 * - 线程安全如何保证？（MeetingState 的并发写入需要同步）
 */
@Component
public class MeetingGraph {

    private static final Logger log = LoggerFactory.getLogger(MeetingGraph.class);

    private final TranscriptionAgent transcriptionAgent;
    private final SummaryAgent summaryAgent;
    private final ActionAgent actionAgent;
    private final InsightAgent insightAgent;
    private final FollowUpAgent followUpAgent;

    public MeetingGraph(
            TranscriptionAgent transcriptionAgent,
            SummaryAgent summaryAgent,
            ActionAgent actionAgent,
            InsightAgent insightAgent,
            FollowUpAgent followUpAgent) {
        this.transcriptionAgent = transcriptionAgent;
        this.summaryAgent = summaryAgent;
        this.actionAgent = actionAgent;
        this.insightAgent = insightAgent;
        this.followUpAgent = followUpAgent;
    }

    /**
     * 执行完整的会议处理 Pipeline
     *
     * 执行流程:
     * 1. Transcription (串行) → 必须先完成转写
     * 2. Summary + Action + Insight (并行) → CompletableFuture.allOf
     * 3. Follow-up (串行) → 等待并行阶段全部完成
     */
    public MeetingState execute(MeetingState state) {
        log.info("Starting meeting pipeline: {}", state.getMeetingId());

        // ============ Pipeline Stage 1: Transcription ============
        state = transcriptionAgent.process(state);
        log.info("Transcription complete, starting parallel processing...");

        // ============ Fan-out Stage: 并行执行 ============
        // 为每个并行 Agent 创建状态副本（避免并发写入冲突）
        final MeetingState stateForSummary = copyState(state);
        final MeetingState stateForAction = copyState(state);
        final MeetingState stateForInsight = copyState(state);

        CompletableFuture<MeetingState> summaryFuture =
                CompletableFuture.supplyAsync(() -> summaryAgent.process(stateForSummary));
        CompletableFuture<MeetingState> actionFuture =
                CompletableFuture.supplyAsync(() -> actionAgent.process(stateForAction));
        CompletableFuture<MeetingState> insightFuture =
                CompletableFuture.supplyAsync(() -> insightAgent.process(stateForInsight));

        // 等待所有并行 Agent 完成
        CompletableFuture.allOf(summaryFuture, actionFuture, insightFuture).join();

        // ============ Fan-in Stage: 合并结果 ============
        try {
            state.setSummary(summaryFuture.get().getSummary());
            state.setActionItems(actionFuture.get().getActionItems());
            state.setInsights(insightFuture.get().getInsights());

            // 合并错误
            state.getErrors().addAll(summaryFuture.get().getErrors());
            state.getErrors().addAll(actionFuture.get().getErrors());
            state.getErrors().addAll(insightFuture.get().getErrors());
        } catch (Exception e) {
            log.error("Error merging parallel results: {}", e.getMessage());
            state.getErrors().add("ParallelMerge: " + e.getMessage());
        }

        log.info("Parallel processing complete, starting follow-up...");

        // ============ Pipeline Stage 3: Follow-up ============
        state = followUpAgent.process(state);

        log.info("Meeting pipeline completed: {}", state.getMeetingId());
        return state;
    }

    /**
     * 快速运行演示模式
     */
    public MeetingState runDemo() {
        MeetingState state = MeetingState.builder()
                .meetingId("demo-" + UUID.randomUUID().toString().substring(0, 8))
                .status("created")
                .build();
        return execute(state);
    }

    private MeetingState copyState(MeetingState original) {
        return MeetingState.builder()
                .meetingId(original.getMeetingId())
                .status(original.getStatus())
                .transcript(original.getTranscript())
                .transcriptText(original.getTranscriptText())
                .errors(new java.util.ArrayList<>(original.getErrors()))
                .build();
    }
}
