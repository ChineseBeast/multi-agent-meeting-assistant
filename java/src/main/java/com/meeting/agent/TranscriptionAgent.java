package com.meeting.agent;

import com.meeting.model.MeetingState;
import com.meeting.model.TranscriptSegment;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Transcription Agent（转写Agent）- Java版
 *
 * Java 版通过 REST API 调用 Whisper 服务（而非本地加载模型）。
 * 无音频时使用演示数据，与 Python 版行为一致。
 *
 * 面试考点:
 * - Java版为什么不直接跑 Whisper？（JVM 生态缺少原生绑定，通过 API 更工程化）
 * - 如何保证 API 调用的可靠性？（重试 + 超时 + 熔断器）
 */
@Component
public class TranscriptionAgent {

    private static final Logger log = LoggerFactory.getLogger(TranscriptionAgent.class);

    public MeetingState process(MeetingState state) {
        log.info("[TranscriptionAgent] Processing meeting: {}", state.getMeetingId());
        state.setStatus("transcribing");

        byte[] audioData = state.getAudioData();
        if (audioData == null || audioData.length == 0) {
            log.info("[TranscriptionAgent] No audio data, using demo transcript");
            state.setTranscript(generateDemoTranscript());
        } else {
            // 生产环境：调用 Whisper REST API
            // 此处简化为演示数据
            state.setTranscript(generateDemoTranscript());
        }

        state.setTranscriptText(formatTranscriptText(state.getTranscript()));
        log.info("[TranscriptionAgent] Transcription complete: {} segments",
                state.getTranscript().size());
        return state;
    }

    private List<TranscriptSegment> generateDemoTranscript() {
        return List.of(
            TranscriptSegment.builder()
                .speaker("张总").text("好的，我们开始今天的Q3预算评审会议。首先请李明汇报一下目前的预算执行情况。")
                .start(0.0).end(8.5).confidence(0.96).build(),
            TranscriptSegment.builder()
                .speaker("李明").text("好的张总。截至目前，Q2预算执行率为87%，其中研发投入占比最大，达到42%。")
                .start(9.0).end(16.2).confidence(0.95).build(),
            TranscriptSegment.builder()
                .speaker("李明").text("Q3我们计划将预算上调15%，主要增加在AI基础设施和人才招聘方面。")
                .start(16.5).end(23.1).confidence(0.94).build(),
            TranscriptSegment.builder()
                .speaker("王芳").text("关于人才招聘，我建议我们重点招聘3名高级算法工程师，预算大概在每人年薪80万左右。")
                .start(23.5).end(31.0).confidence(0.93).build(),
            TranscriptSegment.builder()
                .speaker("张总").text("可以。李明你来负责整理Q3的详细预算方案，下周五之前提交给我审批。")
                .start(31.5).end(38.2).confidence(0.97).build(),
            TranscriptSegment.builder()
                .speaker("张总").text("王芳负责拟定招聘JD，本周三前完成。另外，赵伟跟进一下服务器采购的事情。")
                .start(38.5).end(46.0).confidence(0.95).build(),
            TranscriptSegment.builder()
                .speaker("赵伟").text("收到，我这边已经在对比几家供应商了，预计下周一可以给出采购方案。")
                .start(46.5).end(52.8).confidence(0.94).build(),
            TranscriptSegment.builder()
                .speaker("张总").text("好的，那今天的会议就到这里。各位辛苦了，请大家按时完成各自的任务。")
                .start(53.0).end(59.5).confidence(0.96).build()
        );
    }

    private String formatTranscriptText(List<TranscriptSegment> segments) {
        StringBuilder sb = new StringBuilder();
        for (TranscriptSegment seg : segments) {
            sb.append(String.format("[%.1fs-%.1fs] %s: %s%n",
                    seg.getStart(), seg.getEnd(), seg.getSpeaker(), seg.getText()));
        }
        return sb.toString();
    }
}
