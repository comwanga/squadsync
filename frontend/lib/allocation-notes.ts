// Human-readable note about how free-text "Other" strengths were categorized.
export function normalizationNote(aiNormalized = 0, autoNormalized = 0): string | null {
  if (aiNormalized > 0) {
    const s = aiNormalized === 1 ? "" : "s";
    return `${aiNormalized} free-text "Other" response${s} categorized with the optional helper.`;
  }
  if (autoNormalized > 0) {
    const s = autoNormalized === 1 ? "" : "s";
    return `${autoNormalized} free-text "Other" response${s} categorized automatically.`;
  }
  return null;
}
