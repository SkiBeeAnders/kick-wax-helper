/**
 * waxChooser.js
 * Inputs:
 *  - temperatureC: number
 *  - snowType: "dry" | "transformed" | "wet"
 *  - data: JSON object (as above)
 * Options:
 *  - marginC: widen the temp window (default 1°C)
 *  - maxResults: default 3
 */
export function chooseGripWax(temperatureC, snowType, data, opts = {}) {
  const marginC = opts.marginC ?? 1;
  const maxResults = opts.maxResults ?? 3;

  const products = data.products ?? [];

  // 1) Snow gate: prioritize klister when wet
  const preferType =
    snowType === "wet" ? ["klister", "hardwax"] : ["hardwax", "klister"];

  // 2) Filter: snow tag match + temperature window
  const candidates = products.filter((p) => {
    const tagMatch = (p.snow || []).includes(snowType);
    if (!tagMatch) return false;

    const min = p.temp_c?.min;
    const max = p.temp_c?.max;
    if (typeof min !== "number" || typeof max !== "number") return false;

    return temperatureC >= (min - marginC) && temperatureC <= (max + marginC);
  });

  // 3) Scoring / ranking
  function transformedBias(p) {
    if (snowType !== "transformed") return 0;
    const notes = (p.notes || []).join(" ").toLowerCase();
    let score = 0;
    if (notes.includes("hard track")) score += 6;
    if (notes.includes("tar")) score += 5;
    if (notes.includes("special")) score += 3;
    // Prefer "harder" in overlap: lower max temp is often "colder/harder"
    // small bias toward lower max temp
    score += Math.max(0, (0 - (p.temp_c?.max ?? 0))) * 0.2;
    return score;
  }

  function tempFitScore(p) {
    const min = p.temp_c.min;
    const max = p.temp_c.max;
    const center = (min + max) / 2;
    const span = Math.max(0.1, max - min);
    // Higher is better: closer to center + narrower span
    const dist = Math.abs(temperatureC - center);
    return 10 / (1 + dist) + 2 / span;
  }

  function typePriorityScore(p) {
    const idx = preferType.indexOf(p.type);
    return idx === -1 ? 0 : (preferType.length - idx) * 10;
  }

  const ranked = candidates
    .map((p) => {
      const score =
        (p.priority ?? 50) +
        typePriorityScore(p) +
        transformedBias(p) +
        tempFitScore(p);
      return { ...p, _score: score };
    })
    .sort((a, b) => b._score - a._score)
    .slice(0, maxResults);

  // 4) Add warnings / guidance
  const warnings = [];
  const nearZero = temperatureC >= -1 && temperatureC <= 1;

  if (nearZero && (snowType === "wet" || snowType === "transformed")) {
    warnings.push(
      "Near 0°C: icing risk. If you get icing or slipping, consider klister or a thin klister base under hardwax."
    );
  }
  if (temperatureC < -15) {
    warnings.push(
      "Very cold snow: apply thin layers, cork well, and consider a colder/harder wax."
    );
  }

  return { results: ranked, warnings };
}
