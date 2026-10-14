# Synthetic helpdesk fixture

All records, judgments, code meanings, and dates in this directory are invented.
This fixture demonstrates ingestion, investigation, extraction, artifact use,
and assessment mechanics. **Real-data validation is pending.** Agreement on this
fixture does not establish extraction quality, future reliability, or better
real-world decisions.

The bounded task is to reproduce provisional historical routing judgments for
routine helpdesk intake. A complete target set can contain billing, privacy,
delivery, and escalation; a resolved empty set explicitly records no route.
The examples describe historical practice, not an authoritative routing standard.

## Files and split

| File | Role |
| --- | --- |
| `task.json` | Task intent, pre-decision input meanings, label semantics, scope, and bounded discovery settings. |
| `codebook.json` | Versioned pre-decision intake taxonomy, with opaque aliases resolved to a topic. It contains no target mappings. |
| `development.jsonl` | 50 invented source records from January 1 through February 19, 2026. Use these for inspection, investigation, and artifact development. |
| `assessment.jsonl` | 20 separate invented cases from April 1 through April 20, 2026. Use these only after freezing the artifact. |

Development has 45 resolved, 3 unannotated, and 2 disputed judgments. Assessment
has 18 resolved, 1 unannotated, and 1 disputed judgment. Every row represents a
distinct fictional case group; IDs and group IDs are disjoint between splits.
Identical input combinations across different groups intentionally represent
independent cases, including conflicting judgments. The split is not a random
partition or a sample from a real population.

Each record has `id`, `group_id`, `observed_at`, `inputs`, and `judgment`.
Optional `tags` and `notes` identify diagnostic strata and explain deliberate
edge cases; they are not decision inputs. The assessment deliberately omits
an input in two records to exercise the consumer's missing-information behavior.
Those records retain invented resolved judgments for diagnostic evaluation.

## What the fixture makes investigable

`intake_code` is assigned before the routing judgment. Its meaning depends on
the explicitly declared `synthetic-intake-v1` reference. Multiple codes denote
the same topic; assessment includes codebook-known aliases that never appear
in development. Guessing code meanings or memorizing observed code-to-label
pairs therefore has visible limits.

Development contains repeatable relationships between resolved topic,
`expedited`, and target sets. In the supported routed-topic cells, expedited
handling adds escalation. Information-only non-expedited cases supply explicit
empty target sets, and mixed-account cases supply multiple targets. Channel is
correlated with topic but has counterexamples in development and crossed cases
in assessment, so it cannot safely substitute for reference resolution.

The fixture also retains consequential limits:

- A shipment/non-expedited cell contains three delivery judgments and one
  contradictory billing judgment. An unclear-topic cell contains identical
  available inputs split evenly between billing and privacy judgments.
- Expedited information-only intake has one resolved development example,
  below the declared minimum support. Unannotated records do not increase that
  labeled support.
- Exceptional and experimental scopes lie outside the declared routine scope.
- Unknown codes cannot be interpreted using the supplied codebook.
- Unannotated judgments have `targets: null` and provide no positive or negative
  labels. Disputed judgments have `targets: null` and alternative complete
  `acceptable_targets` sets; preserve that uncertainty in assessment.

These are intentional opportunities for abstention or visible disagreement,
not cases to conceal in an aggregate agreement score. No synthetic passing
accuracy threshold is specified. The hand-designed assessment can demonstrate
generalization mechanics and failure handling; it cannot validate a discovered
method for the eventual real task.

For the command-line workflow, use the repository's main README.
