// Human-readable note about how free-text "Other" strengths were categorized.
export function normalizationNote(aiNormalized = 0, autoNormalized = 0): string | null {
  if (aiNormalized > 0) {
    const s = aiNormalized === 1 ? "" : "s";
    return `🧠 AI categorized ${aiNormalized} free-text "Other" response${s}.`;
  }
  if (autoNormalized > 0) {
    const s = autoNormalized === 1 ? "" : "s";
    return `${autoNormalized} "Other" response${s} categorized automatically — set ANTHROPIC_API_KEY for AI.`;
  }
  return null;
}
