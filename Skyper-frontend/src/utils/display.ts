/** Human-readable labels; keep API identifiers unchanged. */
export function answerReasonLabel(code: string): string {
  const labels: Record<string, string> = {
    NO_EVIDENCE: '未找到依据',
    LOW_CONFIDENCE: '证据不足',
    INTERRUPTED: '已停止生成',
    REQUEST_FAILED: '请求失败',
  }
  return labels[code] ?? '未能完成回答'
}
