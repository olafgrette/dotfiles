---
name: agent-commit-planning
description: Create and operate human-steered, rolling-wave multi-commit plans for substantial software work executed by agents. Use when work needs a durable overall plan, intentionally designed shared contracts or abstractions, small batches of executable commit briefs, and replanning from observed results. Also use for multi-agent implementation handoffs or when controlling code volume and speculative architecture across a large change. Do not use for ordinary implementation, a single commit, or an informal short plan.
---

# Run a human-steered rolling implementation plan

Keep two planning horizons: a human-reviewed overall design and executable briefs only for the next stable batch. Execute that batch, reconcile the plan with the repository, then brief the next batch. Derive commit count from the work; treat a user-supplied count as a review-size constraint or ceiling, not a target to fill.

Use these terms consistently:

- **Slice**: one independently coherent, verifiable unit in the overall plan; its intended deliverable is one commit-shaped change.
- **Brief**: the executable instructions for one near-term slice.
- **Batch**: one to three briefs prepared and executed before reconciliation.
- **Learning gate**: the first unresolved decision, risky result, or contract question whose answer can change later slices.

Planner, executor, and human are logical roles; one agent may perform them sequentially. The planner owns planning artifacts. The executor owns source changes for the current brief. The human approves durable boundaries and material amendments, unless that authority was explicitly delegated.

## Enter at the current state

Inspect the repository and any existing planning artifacts, then take only the next authorized action:

1. **Draft**: if no approved plan exists, inspect the repository and draft only the overall plan and execution constraints. Stop for approval.
2. **Approve**: record human-approved scope, contracts, constraints, and first learning gate in the plan. Approval discussion is not a commit.
3. **Brief**: if the relevant plan decisions are approved, write one to three executable briefs through the next learning gate. Stop after three even if more slices are known.
4. **Execute**: only when implementation was requested, execute the briefed batch sequentially and verify every brief.
5. **Reconcile**: update the overall plan from actual behavior, diff size, verification, and newly discovered constraints; obtain approval for material amendments; then return to Brief.
6. **Complete**: when every requirement is satisfied, required verification passes, no slices remain, and actual volume is reconciled, mark the plan complete.

Do not invent a target architecture from requirements alone. If the repository or a material human decision is unavailable, record the missing input and stop at a coarse slice sketch; do not fabricate file paths, contracts, line estimates, or executable briefs.

## Establish the human approval surface

Inspect the relevant repository structure, current checks, conventions, and existing behavior. Have the human approve, or explicitly delegate decisions about:

- requirements and non-goals;
- the production-code size envelope;
- shared types, signatures, schemas, and intended abstractions;
- external interfaces and compatibility requirements;
- irreversible choices and material scope changes.

Record plan state as `draft`, `approved`, `executing`, or `complete`. Mark cross-commit decisions individually when only part of the plan is approved. Never infer approval from silence or from the existence of a draft.

Let the executor decide commit-local implementation details. Specify cross-commit decisions precisely and once; do not implement the project in prose.

After inspection, propose the smallest plausible target file tree with per-file production-line estimates and a total. Treat a user-supplied size range as context or a ceiling, never as a minimum. For every file and abstraction, name the current requirement, repository convention, consumer, or observed pain that justifies it. Delete anything without one.

When a separate context is available, give a fresh reviewer only the requirements, non-goals, proposed tree, estimates, and stated justifications. Ask it to identify every untraceable element and propose the smallest plan that still satisfies the requirements. Do not include the original planner's defense.

## Separate planning state by audience

Default to conversation-only output. Create planning files only when the user authorizes persistent artifacts. Follow an existing repository convention for their location; otherwise ask where the planning bundle belongs and whether it should be tracked before writing it. Creating or updating planning files never authorizes source changes or git commits.

- Compiling source is authoritative for approved shared contracts.
- `PLAN.md` is the human and planner view of the whole effort.
- `CONSTRAINTS.md` is the portable execution contract given to every executor.
- `commits/SNN.md` is the brief for stable slice identifier `SNN`.

Never renumber a slice identifier. Reordering changes only `PLAN.md`; splitting creates new identifiers; invalidated briefs are marked `superseded`, not silently reused.

### `PLAN.md`

Include:

- plan state, goal, requirements, and explicit non-goals;
- approved architectural decisions and references to contracts in source;
- target file tree, per-file estimates, and total production-code budget;
- an ordered slice list with stable IDs, status, estimate, dependencies, and learning gates;
- unresolved decisions and the conditions under which the plan must be revisited.

Keep each future slice to roughly one line. Do not duplicate source signatures or write full briefs for the entire project.

### Volume accounting

Count production volume as added lines in hand-written, non-test source paths. Report deletions separately; they do not offset additions. Report test additions separately and do not cap verification required by the brief. Exclude generated and vendored files. Define project-specific production, test, and generated paths in `CONSTRAINTS.md`.

Before execution, record the comparison baseline and any pre-existing modifications; preserve and exclude unrelated work. Use `git diff --numstat` when it represents the brief's delta, but do not require a particular counter when repository tooling provides a better one.

Plan with per-file production additions and a total. Give every brief a production-addition estimate. Stop when likely production additions exceed `1.5x` that estimate. During reconciliation report production additions, production deletions, and test additions against the estimate.

### `CONSTRAINTS.md`

Copy this framework section verbatim, then append project constraints with the reason for each:

```markdown
## Execution framework

- Work only on the current brief; do not implement future slices.
- Treat PLAN.md and other briefs as planner-owned and read-only. Do not use future-plan knowledge to shape the current implementation.
- Edit only the source paths named by the brief. Stop if another path is required.
- Do not add abstractions, configuration, or extension points for hypothetical future consumers.
- Do not change an approved shared contract unless the brief is an approved contract-amendment slice.
- Stop if the brief requires a new or changed shared contract.
- Stop if production additions are likely to exceed 1.5x the brief estimate.
- Stop if repository state materially contradicts an assumption in the brief.
- Stop before unapproved destructive, externally visible, or irreversible work.
- A brief is incomplete until its required verification passes. Never weaken verification or continue to another brief with a known failure.
- Report production additions, production deletions, and test additions against the recorded baseline.
- Do not edit planning artifacts or run git commit unless explicitly authorized.

## On stop

Stop editing. Do not commit, revert, or discard partial work. Report `STOP_REASON`, completed changes, current working-tree state, exact triggering evidence or failed verification, and the smallest amendment likely to unblock execution.

## Project constraints

- Define production, test, generated, and vendored paths for volume accounting.
```

Do not use adjectives such as "clean", "simple", or "pragmatic" as constraints. Name the prohibited behavior or required invariant.

### `commits/SNN.md`

Write one to three briefs through the next learning gate. Keep each brief under roughly 200 words and include:

- proposed commit title matching repository convention;
- observable outcome or explicitly named risk reduced;
- affected paths;
- approved contracts it consumes or amends;
- production-addition estimate and comparison baseline;
- exact verification;
- explicit non-goals and dependencies;
- any commit-specific stop condition.

Reference source contracts rather than restating them. Do not include implementation code. A brief must be executable from current repository state; keep approvals, investigations, and unresolved decisions as gates in `PLAN.md`, not commits. A commit-shaped brief does not authorize running `git commit`.

## Order commits by evidence

Prefer independently coherent, verifiable vertical slices over layers:

1. Establish any missing automated check required to verify later slices and any already-approved external or proven contract needed by several of them.
2. Build the thinnest end-to-end path that gives the design a real consumer.
3. Implement the slices with the greatest uncertainty or architectural risk.
4. Implement remaining behavior in dependency order.
5. Add a second implementation only after the first has a live consumer and the second is required by current scope.
6. Perform cutover and remove superseded paths in reversible increments.

Land a standalone contract before its consumer only when its shape is externally imposed, proven by existing code, or required for parallel work. Human approval is necessary for a designed cross-commit contract, but approval alone does not require a separate contract commit; otherwise introduce the approved boundary with its first consumer.

Include tests, error handling, observability, and required operational behavior in the slice they support; do not defer them to a generic hardening phase. Prefer concrete code until an abstraction has a current justification. Require an existing consumer for configuration and a caller that branches before splitting error types. Treat interfaces, wrapper layers, plugin systems, registries, hooks, event buses, and rules engines as non-exhaustive examples requiring a current consumer, externally imposed boundary, or explicit repository convention.

## Execute and replan

Prefer an isolated execution context containing only current repository state, `CONSTRAINTS.md`, and one current brief. Isolation is optional: when executing in the planning context, work solely from the brief and constraints and do not act on future-plan knowledge.

Execute briefs sequentially. A brief completes only when its verification passes. After the batch, the planner:

1. compares actual behavior, files, and volume with estimates;
2. updates completed slice status and assumptions invalidated by the work;
3. reorders, splits, combines, or removes future slices using the new evidence;
4. marks invalidated briefs `superseded` and never reuses their identifiers;
5. obtains human approval for material changes to scope, architecture, shared contracts, or external effects;
6. briefs the next batch and repeats.

After an executor stop, inspect the evidence and propose the smallest plan or contract amendment. Update the budget and affected downstream slices. Land an approved contract change explicitly before dependent work; never let it drift into an unrelated implementation slice.

Finish by setting the plan state to `complete`, recording final verification and volume against budget, and leaving no pending or executable briefs.
