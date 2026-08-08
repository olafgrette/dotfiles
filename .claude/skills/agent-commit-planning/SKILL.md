---
name: agent-commit-planning
description: Structure a multi-commit implementation plan that agents will execute, without the output ballooning into an overengineered mess. Use this whenever work is being broken into a sequence of commits, whenever one agent is writing a plan or briefs for other agents to implement, and whenever the user is deciding how much detail a plan needs. Trigger on "break this into commits", "plan this out", "write the implementation plan", "how should I sequence this", or any sign the user is worried an agent will generate too much code or over-abstract. Do not wait for the word "plan" — a request to build something substantial in stages is a request for this.
---

# Planning commits for agents to execute

An agent handed a substantial build target reliably produces more code than the target requires: interfaces with one implementation, config systems with one caller, layers designed against imagined requirements. Nothing in the objective penalizes the twelfth file, and plans that enumerate more read as more thorough. Every rule here exists to put a cost on volume.

Note also that a stated commit count is itself a bloat instruction — an agent told "fifteen to twenty commits" will find twenty things to do. Derive the count from the slice list after the slice list is fixed.

## Resolution tracks blast radius

The tension between over- and underspecifying dissolves once the plan stops being one document at one resolution.

Anything crossing a commit boundary — types, signatures, error shape, module layout, naming — is specified exactly, once, globally. Anything internal to a single commit gets a sentence. A bad decision inside one commit is a cheap revert; a bad decision on a shared contract propagates into everything after it and is what actually produces the mess.

Note that stacking structural constraints has a measurable cost in functional correctness, so spend the constraint budget only where the blast radius justifies it.

## The first commit is types

Shared types and signatures land in the repository as the first commit — real, compiling code that everything after builds against. Not prose, and not a document living beside the plan; if it compiles it belongs in the tree.

This is where opinions about what the interfaces should look like belong. Expressed as signatures they become the thing agents code against; restated as prose across several briefs they drift, because each restatement differs slightly and the agent reconciles the difference by inventing.

Freezing is enforced by rule, not by where the files sit — see the constraint below about adding fields. An executing agent treats ordinary source files as editable unless told otherwise.

Specify what things *are*. Do not specify how their insides work — that is genuine overspecification and it is where the correctness cost starts.

## Constraints, with reasons

One `CONSTRAINTS.md` in context for every commit. State why with each rule; bare rules get followed literally and generalize badly to the cases nobody enumerated. Start from:

- No interface with one implementation unless a second is built within these commits. Not planned, not likely — built.
- No abstraction before the third occurrence of the duplication it removes.
- No config value with only one caller.
- No plugin, registry, hook, event bus, or rules engine.
- One error type until a caller demonstrably needs to branch on the difference.
- No new fields or methods on the types from the first commit. Stop and ask instead.
- Per-commit line budget, reported as actual against estimate. Exceeding it by half is a stop-and-review, not a note in the summary.

Adjectives do not constrain. "Clean", "simple", and "pragmatic" are no-ops — the agent already believes it is doing that. Name the specific pattern being banned.

Budgets only bite if something checks them. A budget nobody verifies is decoration.

## Slice, don't layer

Layer-ordered commits mean nothing runs until the last one: no feedback, no integration signal, and budget overruns invisible until the end. Worse, designing a layer before its callers exist is the single largest generator of speculative abstraction — the storage layer gets built against imagined queries.

Order by end-to-end path. Each commit changes observable behavior and is verifiable on its own.

The first commit is the deliberate exception: scaffolding, the frozen types, and whatever automated check the later commits will be verified against. It changes no behavior and the only thing proving it is that it compiles. That is fine — its verification is every commit after it. Nothing else gets that exemption.

The exception is a component whose contract came from outside — a wire format, a protocol, a third-party API. Those are independently verifiable because someone else defined the shape, so building them standalone is fine. The test is the origin of the contract. If the agent decided what the interface looks like, it needs a real consumer before it is real.

Build the second implementation of anything only after the first has a live caller. Two implementations built against each other with no consumer get shaped to fit each other rather than to fit use.

## Two plan resolutions

- `PLAN.md` — ordered slice list. One line and a line budget per slice.
- `commits/NN.md` — full brief, written only for the next few.

Do not write all briefs up front. Briefing commit twelve before commit two exists anchors the executing agent to a shape the intervening work may already have invalidated. Depth should track how much the plan learns per commit: shallow while contracts are still settling, deeper once the shape has stopped moving and the remaining work is mechanical. The rule is *do not brief past the next thing that could change the plan*.

Cap each brief at roughly fifteen lines: what observable behavior changes, which files, line estimate, what proves it done, what it explicitly does not do. No code except references to already-frozen signatures. An unconstrained planning agent writes half the implementation into the brief, which pays for the code twice and locks in decisions before the executing agent has seen the repository.

## Make the agent stop rather than invent

Standing rule for executing agents: **if you need a type, signature, or contract that the first commit did not establish, do not create one — stop and ask.**

This converts underspecification from silent divergence into a visible question, which means the plan's resolution does not have to be right in advance. It will not be.

The stop rate is the feedback signal on that resolution. Zero stops means overspecification — effort spent on decisions nobody needed. Constant stops means the contracts are too thin. A couple per commit is about right.

## Autonomy is bought with verification

Long unattended runs are achievable, but front-loaded briefs buy nothing except autonomy on stale information. What actually buys it: an automated check that can run without a human, frozen contracts, a budget check, and the stop-and-ask rule. An agent so equipped runs several commits deep and returns either a stack of green diffs or one specific question.

Do not over-rely on human review as the quality gate either. Reviewing every few commits works only if the diffs are read closely, and at a few hundred lines each that decays fast — three rounds in, skimming and approving is worse than no gate, because it launders the code as reviewed. Mechanical checks do not decay. Spend human attention on the boundaries where judgment is genuinely required: the first commit that consumes a new shared abstraction, the first that performs a real side effect.

## When converting existing working code

The automated check above is the hard part, and existing code solves it — the old implementation is an oracle for correct behavior, and its structure is evidence about where the real seams are. If a working prototype or legacy version exists, get the replay harness standing before planning anything, and treat commits as *extraction* (moving determined content, behavior-preserving) versus *construction* (new code). A conversion plan heavy on construction commits means the agent decided the new version needs things the old one never had.
