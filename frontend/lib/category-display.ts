import { CONCRETE_STRENGTHS } from "@/lib/taxonomy";

const KNOWN = new Set<string>(CONCRETE_STRENGTHS.map(s => s.value));

/** True when the value is one of the selectable universal categories. */
export function isKnownStrength(value?: string): boolean {
  return !!value && KNOWN.has(value);
}

/**
 * Human-readable text for a Category cell whose value isn't a selectable option
 * — i.e. a free-text "Other" that was fallback-normalized (slug) or not yet
 * normalized. Prefer the original free text, else de-slug the normalized value,
 * else a generic prompt.
 */
export function categoryPlaceholder(p: { normalized_strength?: string; strength_other?: string }): string {
  if (p.strength_other?.trim()) return p.strength_other;
  if (p.normalized_strength?.trim()) return p.normalized_strength.replaceAll("_", " ");
  return "Set category";
}
