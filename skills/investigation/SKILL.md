---
name: investigation
description: Run evidence-first technical investigations with falsifiable hypotheses, read-only collection, a durable evidence ledger, and reproducible data views for human inspection. Use for incident analysis, production or SRE debugging, dataset exploration, log/metric/trace analysis, root-cause work, or other multi-step investigations where findings, refuted paths, provenance, and next actions must persist. Do not use for a single direct lookup or ordinary implementation.
---

# Run an evidence-first investigation

Keep target systems, infrastructure, datasets, and project sources read-only unless the user explicitly authorizes mutations. An investigation request does not authorize fixes or source changes.

For an extended investigation, reuse an existing or user-designated Markdown log. If no path is designated, ask once before creating it. Creating or updating the log authorizes only that artifact.

## Investigate

1. Frame the question, systems, time bounds, constraints, and what evidence would change the conclusion.
2. State falsifiable hypotheses with stable IDs and statuses: `open`, `supported`, or `refuted`. Treat `supported` as provisional. Retain refuted hypotheses and their evidence.
3. Choose the least costly read-only test that best distinguishes the live hypotheses. Seek disconfirming evidence before accumulating confirmation.
4. Prefer parameterized, rerunnable queries or scripts for collection, joins, and formatting. Preserve the query and transformations; redact credentials and tokens.
5. Check the data representation before interpreting it. Record the material checks:
   - volume and bounds: row counts, time bounds, sampling, and filters;
   - quality: missingness and duplicates;
   - transformations: aggregation windows, join keys/cardinality/fan-out, and unmatched rows;
   - distribution: tails and relevant extremes.
6. Update the log after each evidence-producing step and before changing direction. Record negative results so later agents do not repeat them.
7. Present inspectable evidence before interpretation. Include representative raw rows and relevant extremes with identifiers when feasible; do not collapse the result into an agent-only summary.

## Maintain the log

Use this minimal structure and extend it only when the investigation needs more detail:

```markdown
# Investigation: <question>

## Scope
- Systems/data:
- Time bounds:
- Constraints:

## Hypotheses
| ID | Hypothesis | Status | Disconfirming test | Evidence |
|---|---|---|---|---|

## Timeline and evidence
| Time | Action/query | Result | Source/link |
|---|---|---|---|

## Representation choices
- Sampling/filtering:
- Missingness/deduplication:
- Aggregation/granularity:
- Joins/cardinality:

## Findings
### Observed
### Inferred

## Unknowns and next actions

## Reusable methods
```

Link evidence from the hypothesis table instead of duplicating it. Keep exact commands and queries when safe; never store secrets. Record why a path was refuted, not only its status.

## Prepare evidence for human inspection

- Put the data-trust preamble before the main output: source/query version, row count, time range, and material quality checks.
- Make filters, time windows, bucket sizes, and limits parameters when practical so the user can reslice without another agent round trip.
- Preserve tails and exemplars. Include useful quantiles and worst cases with identifiers when aggregates could hide the signal.
- Report negative space: what was checked, what came back clean, and how it was ruled out.
- Separate evidence from interpretation and place interpretation last to avoid anchoring the user's review.

## Hand off or finish

Update the log before handoff. State the strongest supported and refuted hypotheses, material limitations, open unknowns, and the next discriminating action. Do not present a provisional hypothesis as confirmed.
