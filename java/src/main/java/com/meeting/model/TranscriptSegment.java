package com.meeting.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 单条转写片段 - 包含说话人和时间戳
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TranscriptSegment {

    private String speaker;
    private String text;
    private double start;
    private double end;

    @Builder.Default
    private double confidence = 0.0;
}
