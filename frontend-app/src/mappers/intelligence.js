// Normalizes platoon/battalion intelligence DTOs to UI-friendly shapes.

export function mapTankScore(raw) {
  if (!raw) return null;
  return {
    id: raw.tank_id,
    score: raw.score,
    grade: raw.grade,
    gaps: raw.critical_gaps || [],
    topMissing: raw.top_missing_items || [],
    family: raw.family_breakdown || raw.breakdown || {},
    deltas: raw.deltas || {},
    gapCounts: raw.gap_counts || {},
    trend: raw.trend || [],
  };
}

export function mapPlatoonIntel(raw) {
  if (!raw) return null;
  const tanks = (raw.tank_scores || []).map(mapTankScore).filter(Boolean);
  return {
    platoon: raw.platoon,
    week: raw.week,
    score: raw.readiness_score,
    breakdown: raw.breakdown || raw.family_breakdown || {},
    deltas: raw.deltas || {},
    coverage: raw.coverage || {},
    criticalCount: raw.critical_tanks_count || 0,
    topGaps: raw.top_gaps_platoon || raw.top_gaps_battalion_level || [],
    tanks,
  };
}

export function mapBattalionIntel(raw) {
  if (!raw) return null;
  const platoons = Object.entries(raw.platoons || {}).map(([name, p]) => ({
    name,
    score: p.readiness_score,
    delta: p.deltas?.overall || p.delta,
    gapsByFamily: p.gaps_by_family || {},
    coverage: p.coverage || {},
    trend: p.trend || [],
  }));
  return {
    week: raw.week,
    score: raw.overall_readiness,
    deltas: raw.deltas || {},
    comparison: raw.comparison || {},
    topGaps: raw.top_gaps_battalion || [],
    platoons,
  };
}
