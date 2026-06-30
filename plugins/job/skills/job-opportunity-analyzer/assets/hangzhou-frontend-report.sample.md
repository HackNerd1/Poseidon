# Hangzhou Frontend Opportunity Sample Report

> This report is a sample artifact for workflow validation only. Company names, links, and some narrative bridges are illustrative placeholders derived from the local sample JSON, not live recruitment results.

## Analysis Scope

- `location`: `hangzhou`
- `position`: `frontend engineer`
- User filters: focus on `React` / `TypeScript` opportunities, prefer city-local teams, accept both platform and visualization directions
- User-specified companies: none
- Analysis emphasis: `salary transparency`, `role-fit`, `growth potential`, `source traceability`
- Evidence coverage: `3` companies, `3` job opportunity records, `3` sentiment summaries

## Executive Summary

- `hqtrip` is the most stable near-term target because its role facts come from an official job page plus a school-board trace, and no predefined conflict tag blocks comparison. See `opp-hz-001`, `[src-hz-007]`, `[src-hz-008]`.
- `lakeflow-robotics` is the strongest stretch option because the role is highly aligned with advanced frontend visualization work and the growth signal is backed by both official hiring and an expansion news source. The main tradeoff is `experience_unaligned`. See `opp-hz-002`, `[src-hz-009]`, `[src-hz-010]`.
- `qianmu-ai` remains worth tracking, but the current result is weak. The role evidence is third-party only, salary is opaque, and sentiment sampling is still thin, so the sample should not force a strong recommendation. See `opp-hz-003`, `[src-hz-006]`, `[src-hz-014]`, `[src-hz-015]`.
- For this sample dataset, the recommended posture is `mixed-layout`: use `稳妥型` as the main application base, keep one `冲刺型` target, and reserve unclear growth names for follow-up verification instead of immediate prioritization.

## Opportunity Table

| company | role | city | salary | experience | match_reason | strategy_bucket | risk_flags | source_refs | salary_match | source_certainty | growth_signal | sentiment_confidence |
|---------|------|------|--------|------------|--------------|-----------------|------------|-------------|--------------|------------------|---------------|----------------------|
| hqtrip | Frontend Engineer | hangzhou | 20-30K·14薪 | 3年以上 Web 前端开发经验 | React + TypeScript directly matches the target frontend scope, and the travel SaaS platform context suggests steady product-facing demand. | 稳妥型 | none-observed | [src-hz-007], [src-hz-008], [src-hz-011] | match | high | observed | medium |
| lakeflow-robotics | Senior Frontend Visualization Engineer | hangzhou | 28-38K·16薪 | 4-6年，具备复杂工业可视化项目经验优先 | The role combines React, TypeScript, Three.js, and industrial digital-twin work, which makes it the highest-upside visualization track in this sample. | 冲刺型 | experience_unaligned | [src-hz-009], [src-hz-010], [src-hz-013] | partial | high | strong | medium |
| qianmu-ai | Senior Frontend Engineer | hangzhou | 面议 | 5年及以上，具备复杂可视化项目经验优先 | The direction is adjacent to the target frontend profile, but current support still depends on third-party evidence rather than an official role page. | 待人工判断 | salary_unaligned, third_party_only, insufficient_sentiment_samples | [src-hz-006], [src-hz-014], [src-hz-015] | unaligned | low | observed | low |

## Strategy Recommendations

### 冲刺型

- `lakeflow-robotics`
- Why it qualifies:
  - The role-fit is explicit in both stack and domain: `React`, `TypeScript`, `Three.js`, and digital-twin work line up with advanced frontend visualization growth.
  - Growth evidence is not single-source; `[src-hz-009]` confirms the role exists and `[src-hz-010]` supports expansion context.
  - The current downgrade condition is limited to `experience_unaligned`, which weakens accessibility but does not break source certainty.
- Sample-only caveat:
  - This conclusion is still a demonstration judgment built from placeholder public facts in the sample asset. It should not be treated as a live market recommendation.

### 稳妥型

- `hqtrip`
- Why it qualifies:
  - Role facts are official-first and locally reinforced by `[src-hz-008]`.
  - The position requirement is close to a mainstream frontend target profile and does not carry conflict tags in the sample JSON.
  - Sentiment is not fully rich, but the evidence does not currently show concentrated negative signals.

### 待人工判断

- `qianmu-ai`
- Why it stays here:
  - `third_party_only` blocks high-confidence prioritization.
  - `salary_unaligned` prevents clean compensation comparison.
  - `insufficient_sentiment_samples` means the sentiment summary remains supportive but weak.
- What would upgrade it:
  - An official role page, one fresh source for team status, and a clearer salary or experience range.

## Market Summary

- In this Hangzhou sample, `T2` growth-stage companies dominate the higher-upside frontend opportunities, while `T3` names offer more stable but less aggressive upside.
- Visualization-heavy frontend roles appear more differentiated than general product frontend roles in this dataset.
- Official hiring pages make the biggest difference in recommendation strength; when the sample falls back to third-party job boards, recommendation confidence drops quickly.
- The most common risks in this sample are salary opacity, higher-than-target experience thresholds, and thin sentiment coverage.
- This is only a sample-sized observation for workflow validation, not a claim about the entire Hangzhou frontend market.

## Overall Assessment

- Recommended posture: `mixed-layout`
- Reasoning:
  - `稳妥型` opportunities have the strongest source certainty and the cleanest field alignment in this sample.
  - `冲刺型` opportunities offer the strongest growth narrative, but they also demand better experience alignment.
  - At least one growth-stage company still sits behind `third_party_only` and `salary_unaligned`, so the sample should not overstate confidence.

## Company Notes

### hqtrip

- Hiring evidence is supported by `[src-hz-007]`, with local recruiting activity reinforced by `[src-hz-008]`.
- The business context is platform-oriented travel SaaS, which supports a straightforward product frontend path.
- Sentiment is balanced but limited: `[src-hz-011]` and `[src-hz-012]` suggest focused business direction with incomplete team-size visibility.
- Current strategy bucket: `稳妥型`.
- Manual review focus: confirm current team size and whether the role is tied to one product line or a shared platform group.

### lakeflow-robotics

- Hiring evidence is official and recent via `[src-hz-009]`.
- The business and growth signal are stronger than the rest of the sample because `[src-hz-010]` links expansion narrative to the role direction.
- Sentiment shows technical depth but also indicates a faster operating rhythm. See `[src-hz-013]`.
- Current strategy bucket: `冲刺型`.
- Manual review focus: confirm how strict the `4-6` year expectation is and whether equivalent visualization depth can offset the seniority bar.

### qianmu-ai

- Current hiring evidence comes from `[src-hz-006]` only for the role itself, which is why the recommendation remains weak.
- The company still deserves tracking because `[src-hz-005]` and `[src-hz-015]` keep the growth narrative plausible.
- Sentiment is thin and should be treated as supportive context rather than decisive evidence. See `[src-hz-014]`.
- Current strategy bucket: `待人工判断`.
- Manual review focus: verify whether an official hiring page exists and whether the role is still open.

## Fact Sources

- [src-hz-001] industry_list | https://example.com/hangzhou-digital-economy-list | observed: 2026-06-20 | Candidate-pool evidence for `hqtrip`
- [src-hz-002] official | https://jobs.hqtrip.example.com | observed: 2026-06-28 | Company-level hiring existence for `hqtrip`
- [src-hz-003] industry_list | https://example.com/hangzhou-smart-manufacturing-growth-2026 | observed: 2026-06-18 | Growth-list evidence for `lakeflow-robotics`
- [src-hz-004] official | https://www.lakeflow-robotics.example.com/careers | observed: 2026-06-29 | Company-level hiring existence for `lakeflow-robotics`
- [src-hz-005] industry_list | https://example.com/hangzhou-growth-tech-2026 | observed: 2026-06-18 | Growth-list evidence for `qianmu-ai`
- [src-hz-006] job_board | https://example.com/jobs/qianmu-ai-frontend | observed: 2026-06-27 | Role evidence for `qianmu-ai`; also the main reason it stays `third_party_only`
- [src-hz-007] official | https://jobs.hqtrip.example.com/frontend-engineer | observed: 2026-06-28 | Role facts for `hqtrip`
- [src-hz-008] school_board | https://example.com/school-board/hqtrip-campus-frontend | observed: 2026-06-24 | Local recruiting activity for `hqtrip`
- [src-hz-009] official | https://www.lakeflow-robotics.example.com/careers/frontend-visualization | observed: 2026-06-29 | Role facts for `lakeflow-robotics`
- [src-hz-010] news | https://example.com/news/lakeflow-robotics-expansion | observed: 2026-06-22 | Growth signal for `lakeflow-robotics`
- [src-hz-011] community | https://example.com/community/hqtrip-discussion | observed: 2026-06-25 | Team-rhythm context for `hqtrip`
- [src-hz-012] news | https://example.com/news/hqtrip-36kr | observed: 2026-06-21 | Business-stage context for `hqtrip`
- [src-hz-013] community | https://example.com/community/lakeflow-robotics-niuke | observed: 2026-06-26 | Interview-rhythm context for `lakeflow-robotics`
- [src-hz-014] community | https://example.com/community/qianmu-ai-niuke | observed: 2026-06-24 | Limited sentiment context for `qianmu-ai`
- [src-hz-015] news | https://example.com/news/qianmu-ai-local | observed: 2026-06-19 | Business-stage context for `qianmu-ai`

## Missing Data And Exceptions

| item | impact | affected_companies | next_action |
|------|--------|--------------------|-------------|
| salary_unaligned | Weakens direct compensation comparison | qianmu-ai | Find one official or recent recruiter source with a concrete pay band. |
| third_party_only | Lowers source certainty for role existence and role detail confidence | qianmu-ai | Verify whether an official hiring page or company WeChat recruitment post exists. |
| insufficient_sentiment_samples | Makes stability judgment weak | qianmu-ai | Add one more recent community or news source within the last 90 days. |
| experience_unaligned | Reduces near-term accessibility even when upside is high | lakeflow-robotics | Confirm whether equivalent visualization depth can substitute for years-of-experience wording. |
| team-size visibility gap | Keeps stability assessment partial rather than complete | hqtrip | Ask in screening whether the frontend team is product-owned or shared-service. |

## Follow-Up Review Suggestions

- Re-check `qianmu-ai` first, because one official role source would materially change the recommendation from `待人工判断` to a more actionable bucket.
- For `lakeflow-robotics`, focus the next review on scope and leveling rather than business legitimacy, because the current weak point is seniority fit, not source certainty.
- For `hqtrip`, the next useful update is not more role proof but better team-structure context, so a fresh community discussion or interview-note source would be the highest-value addition.
