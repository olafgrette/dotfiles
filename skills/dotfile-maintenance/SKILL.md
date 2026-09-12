---
name: dotfile-maintenance
description: Maintain this dotfiles repository through system-drift capture, guided package and configuration review, reviewed commits and push, and upstream changelog analysis. Use for a dotfiles maintenance pass or release-impact review, not isolated configuration edits.
---

# Dotfile maintenance

Follow the requested stages. A full pass captures current intent, sorts it with
the user, commits and pushes the accepted changes, then reviews upstream releases
and proposes follow-up work. Creating or editing this skill does not start a pass.
Read the repository's AGENTS.md and current scripts before using this workflow;
they define the host gates, config ownership, local overrides, and checks.

## Capture current intent

- Locate the checkout from the skill's resolved path or the user's workspace.
  Inspect Git status and existing diffs before capture so existing work remains
  distinguishable. Check for pending `aconfmgr/99-unsorted.sh` work before a save
  can rewrite it; review that work first.
- On a declared personal Arch host, run `./aconf.sh save` in the foreground.
  This captures system drift for review; it does not apply system configuration.
  If credentials or terminal access prevent completion, ask the user to run it
  in this checkout and report completion. Continue independent release research
  while waiting. On other hosts, skip the system capture and explain the gap.
- Inspect the generated declarations, referenced captured files, and tracked
  diff. `aconf.sh diff` excludes packages and is not a substitute for save.
  The `/etc` allowlist also means save is not an inventory of every system change.
- Review HOME-layer drift through each tool's actual ownership model. For DMS,
  use `dms-settings capture` when capturing GUI preferences is in scope. Its
  capture command can offer commits: defer those until the grouped review below
  (noninteractive stdin suppresses its commit prompts). Keep session state and
  local overrides outside shared capture.

## Sort with the user, then publish

Present small, coherent groups with a recommendation and the decisions needed:
shared intent, hardware-specific intent, local-only change, or unwanted drift.
Distinguish adding/removing a declaration from installing/removing software.
Explain the effect on other machines, especially for captured removals.

- Put accepted common packages in `aconfmgr/20-packages.sh`, shared system
  declarations in `30-system.sh`, and CPU/GPU differences in the matching host
  overlay. Edit the original declaration when appropriate instead of retaining
  generated inverse operations. Inspect referenced file contents before staging.
- Keep temporary choices in the existing local override mechanism. Do not widen
  the system capture scope just to include a generated change. An unwanted live
  change is a recommendation for later convergence, not permission to apply it.
- Account for every generated item. Remove only resolved entries from the
  unsorted file; preserve undecided work. Never stage that ignored file wholesale.
- Run the smallest applicable checks in AGENTS.md. Do not use `install.sh` or
  `aconf.sh apply` as tests. Test stateful helpers against temporary copies when
  useful, rather than changing the running desktop. Run checks directly and
  retain their exit status; piping through `tail` or `grep` can hide failures.
- Show the concrete accepted diff and logical commit grouping. Commit and push
  when the user's request includes those actions; reuse existing authorization
  instead of asking again. A review-only request stops at review. Use scoped
  Conventional Commits with a body explaining why, and stage only reviewed files.
  Verify the branch and push target; report the result and remaining local work.

## Review upstream releases

Use `maintenance-versions.json` as the software inventory and review ledger.
Each entry maps commands to platform package names and records whether the tool
is `reviewed`, `pending`, or `excluded` (with a reason). Reuse these mappings;
check package ownership when adding an entry or when installation changes make a
mapping suspect. Do not rediscover every mapping on every pass.

Focus on top-level tools whose configuration this repository controls: Fish,
Starship, Ghostty, Zellij, tmux, Helix, DMS, and other explicitly inventoried tools.
Review DMS patch notes for its desktop stack; do not separately review greetd,
UWSM, the DMS greeter, or Quickshell in a routine pass. The llama serving tools
are also excluded. Revisit an exclusion only on user request or for a concrete
problem. Hyprland remains relevant to our directly maintained Lua bindings.

When tracked configuration introduces a new review target, add a pending entry.
Do not expand this into a review of every installed package or script dependency.

For each relevant tool:

1. Use the inventory's command/package mapping to establish the installed
   version and relevant configuration paths. Keep upstream projects distinct even
   when they share branding: `dms-shell` provides `dms`; the greeter is separate.
   Missing local installations are coverage gaps, not completed reviews.
2. Read the last reviewed version from `maintenance-versions.json` at the repo
   root, including unresolved notes and findings in the checkpoint commit body.
   Carry still-relevant findings into this pass's report even when no new release
   needs review. Review releases after that checkpoint through the chosen target
   release, including intermediate migration notes. Compare the installed version
   separately: installation is not evidence of review. If no checkpoint exists,
   use available history to establish a review interval, or review the current
   release and its upgrade notes as an explicit initial baseline. Do not claim
   coverage of older releases that were not inspected.
3. Read the patch notes for the release interval. Patch notes are sufficient
   for routine review; source-code audits and additional proof gates are not
   required. Consult help or implementation only to resolve a specific ambiguity.
   A version lookup alone is not a patch-note review. Keep private configuration
   out of external queries.
4. Compare findings with our actual configuration: removed/renamed keys, changed
   defaults, file/state ownership, precedence and local includes, package or
   service changes, IPC/keybind behavior, and features that can replace custom
   scripts or dependencies. Prefer native functionality when it reduces code
   without losing intended behavior.

Before committing checkpoints, report a compact table in chat: tool and reviewed
versions, source link, affected repo paths, implication, and recommendation.
Include checked tools with no actionable change and explicitly list gaps; do not
silently omit unsuccessful lookups.

Keep the inventory and review checkpoints together in `maintenance-versions.json`.
Use upstream versions for checkpoints, not distribution package revisions. For development snapshots, record the full upstream commit and inspect
the intervening commits when release notes do not cover them. Example structure:

```json
{
  "tools": {
    "example-tool": {
      "commands": ["example"],
      "packages": {"arch": ["example-package"]},
      "status": "reviewed",
      "upstream": "https://example.org/project",
      "reviewedThrough": "v2.3.0",
      "reviewedOn": "2026-09-12",
      "source": "https://example.org/project/releases/v2.3.0"
    }
  }
}
```

Add tools before review with `status: pending` and no review checkpoint. Excluded
entries require a `reason` and are skipped during routine review. Set `reviewed`
and advance `reviewedThrough` only after reading the applicable patch notes;
never prefill it with an installed or latest version. Failed or partial reviews
remain pending and keep any previous completed checkpoint. A pending entry with
no checkpoint needs an initial review, even if its installed version is unchanged. Record platform-specific upstream
release streams separately where necessary, without storing hostnames or machine
inventories. A checkpoint records review coverage, not implementation completion;
carry unresolved actionable findings in the checkpoint commit body so the next
pass can retrieve them from Git history. After completing the release review,
commit only the ledger in a separate `chore(maintenance): record reviewed versions`
commit, with that review summary in the body. Keep it separate from captured drift
and implementation changes. Push it under the existing publishing authorization.
For review-only requests, report proposed checkpoint updates without writing or
publishing them.

## Propose follow-up changes

Rank proposals as compatibility fixes, simplifications, or optional features.
For each, state the concrete behavior change, affected files, useful deletions
(including obsolete tests), and the smallest meaningful validation. Separate
observed breakage from inferred risk. Keep findings in chat unless the user asks
for an artifact. Release review ends with proposals; implement them only when
requested, preserving any implementation authorization already given.
