# Logic Foundry prototype

Canonical repository: [Freedom-Jack/logic-foundry](https://github.com/Freedom-Jack/logic-foundry).

A local command-line path from historical source records to reusable decision
logic, evidence, and a separately evaluated reference consumer. Python 3.9+
and the standard library are sufficient; no installation, API keys, or network
services are required. Run commands from this repository directory.

**Only synthetic data is available. Real-data validation is pending.** The
initial project contained `CONCEPT.md`, `MVP.md`, and `RESEARCH.md`, with no
application code or real source collection. The invented helpdesk fixture tests
the mechanics; it does not establish the method's suitability for a real task.

## Run the complete path

```sh
python3 -B -m logic_foundry demo --out build/demo
python3 -B -m unittest discover -s tests -v
```

The demo inspects **development records only**, extracts and exports an artifact,
then reloads that frozen export and applies it to separate assessment cases.
`-B` avoids writing Python bytecode caches; it is optional.

| Output in `build/demo/` | Use |
| --- | --- |
| `artifact.json` | Operational rule table, bundled reference, input meanings, scope, baseline, provenance, and limitations. |
| `application.md` | Required inputs, reference version, output interpretation, and abstention behavior for builders. |
| `profile.json` | Source counts, missingness, value/target distributions, groups, and time range. |
| `evidence.json` | All candidate claims with supporting/conflicting IDs, grouped development comparison, and targeted investigation evidence. |
| `report.md` | Human-readable extraction findings and limits. |
| `evaluation.json` | Complete assessment decisions, metrics, group/target diagnostics, disagreements, abstentions, and unresolved references. |
| `evaluation.md` | Readable assessment report. |

The fixture produces eight rules using resolved intake topic and expedited
status. Of 20 assessment cases, 18 have resolved references: **10 agree, 8
abstain, and none of the decided cases disagree**. Full-collection agreement and
coverage are both 55.6%; the development-majority baseline agrees on 3/18
(16.7%). There are 16 resolved in-scope cases, of which 10 receive decisions
(62.5%). One disputed and one unannotated reference receive no correctness
score. These deliberately constructed cases specify no passing threshold.

## Apply the exported logic to a new case

```sh
python3 -B -m logic_foundry predict \
  --artifact build/demo/artifact.json \
  --input '{"intake_code":"H52","expedited":true,"scope":"routine"}'
```

This returns `status: "decided"` with `targets: ["billing", "escalation"]`, a
matching rule ID, and supporting development record IDs. `H52` is a codebook
alias absent from development records. The unused `channel` input is optional
for this selected artifact. Use `--case /path/to/case.json` to read either an
input object or a record containing `inputs` from a file.

Python consumers can use the same interpreter:

```python
from logic_foundry.consumer import Consumer

consumer = Consumer.from_path("build/demo/artifact.json")
decision = consumer.predict({
    "intake_code": "H52", "expedited": True, "scope": "routine"
})
```

The package and exported JSON suffice at runtime. The consumer reads no source,
assessment, or report files. `targets: []` is an explicit no-route decision;
`status: "abstain", targets: null` means the artifact cannot support a decision.
The latter includes a reason such as missing input, unresolved reference,
conflicted evidence, insufficient support, or outside scope. Builders must
handle abstentions and preserve the supplied input and reference meanings.

## Run each stage separately

```sh
python3 -B -m logic_foundry inspect \
  --task examples/synthetic/task.json \
  --source examples/synthetic/development.jsonl

python3 -B -m logic_foundry fit \
  --task examples/synthetic/task.json \
  --source examples/synthetic/development.jsonl \
  --out build/custom

python3 -B -m logic_foundry evaluate \
  --artifact build/custom/artifact.json \
  --cases examples/synthetic/assessment.jsonl \
  --out build/custom
```

`fit` accepts no assessment argument. Evaluation never fits or changes an
artifact. It rejects overlap in file digest, record IDs, declared case groups,
or exact observation fingerprints (timestamp plus inputs), including unresolved
rows. Fingerprints normalize timezone offsets. Keep related cases in one group;
the guards cannot detect every relationship hidden by changed identifiers and
inputs. Preserve an untouched assessment collection; revising extraction after
seeing it requires fresh assessment material. The fixture assessment dates are
later than development dates; development validation groups by case and does
not simulate temporal drift.

## How discovery works

The inspected synthetic source has categorical/boolean inputs and explicit
target sets. The prototype therefore supports **one artifact family: conditional
rule tables**. The codebook supplies pre-decision topic meanings, with no
routing targets. Raw identifiers and proxy fields are plausible alternatives,
so discovery compares them with reference-resolved fields using development
evidence. Free text, numerical methods, and other artifact families remain
outside this implementation.

1. Validate and profile the source and declared task, including label meaning,
   input availability, case groups, missing values, and scope.
2. Count candidate target sets for individual available fields and pairs.
   Retain supporting, conflicting, and unresolved record IDs for each claim.
3. Choose one bounded investigation: resolve the declared versioned codebook
   when multiple observed IDs make it applicable; otherwise inspect contrasting
   records in a conflicting or supported cell. Record the question, reason,
   evidence, effect, and limits. The investigator is a deterministic policy
   over these two tools.
4. Compare raw-field and, when investigated, reference-resolved tables using
   leave-one-group-out development validation. Task settings specify a minimum
   of two independent supporting groups, up to two fields, and selection utility
   `correct - 3 * incorrect` (abstention earns zero). These fixture-specific
   settings express conservative selection preferences; they are not confidence
   bounds or a validated real-world error tradeoff. Tie-breaking is documented
   in the artifact.
5. Refit the selected table on development records and export repeated,
   unanimous resolved cells. Contradicted cells retain evidence and abstain.
   Unannotated/disputed judgments never supply positive or negative training
   labels. Insufficient evidence may produce zero executable rules.
6. Apply the export through the reference consumer and evaluate separate cases
   against a frozen development-majority target-set baseline.

In the fixture, codebook resolution changes the selected candidate to topic
plus expedited status. Its development comparison records 32 correct, one
incorrect, and 10 abstentions across 43 in-scope resolved references. The
incorrect development prediction occurs when holding out a conflicting
judgment makes the remaining cell unanimous; the full-development artifact
retains that conflict and abstains. Investigation improves input interpretation
without adjudicating which historical judgment is right.

Headline assessment rates use all submitted resolved references, including
outside-scope cases. Automatic scope groups show the bounded applicability
population separately. Reports also show target and optional diagnostic-tag
groups, coverage, agreement across resolved cases, and agreement conditional
on deciding. Disputed alternatives are displayed as diagnostics, never scored
as correctness. Empty denominators produce `null`/undefined rates. There is no
claim of intended-standard correctness, causal benefit, or future reliability.

## Input contract and limits

Use [the synthetic task and source description](examples/synthetic/README.md)
and the included JSON files as the concrete adapter example. A task declares:

- Its historical-reproduction purpose, judgment authority, target IDs, synthetic
  status, and meanings of resolved, unannotated, disputed, and empty judgments.
- One to eight categorical/boolean input fields and their availability at
  decision time; a field/value scope boundary; bounded discovery settings.
- An optional local codebook path (relative to the task file) and expected
  version. Entries map a pre-decision categorical input to a new categorical
  meaning. A declaration of availability is an assumption to verify, not proof
  against target leakage.

Each JSONL record requires `id`, `group_id`, timezone-bearing `observed_at`,
`inputs`, and `judgment`. Resolved targets are complete sets of declared IDs,
including the empty set. Unannotated/disputed targets must be `null`; disputed
judgments may list `acceptable_targets`. Inputs may be missing/null, which is
profiled and handled by abstention. Optional `tags` and `notes` are diagnostics
and never features. Unknown input fields, invalid types/targets, duplicate IDs,
and mismatched reference versions are rejected. A source without resolved
in-scope judgments cannot support historical extraction and fails explicitly.

Artifacts bundle the exact versioned reference, feature transformations/domains,
input requirements, rules, unsupported cells, source hashes, and leakage-guard
identifiers. Stable serialization and no generated timestamps make repeated
runs byte reproducible. Integrity hashes detect accidental edits; they provide
no authentication. Treat exported provenance identifiers as source information
when sharing artifacts.

This is a small-collection prototype: it loads JSONL into memory and uses
leave-one-group-out comparison. Its discovery cost grows with group count and
conditional-cell count; it is not benchmarked for the illustrative 100,000-case
collection. Full profiling and deliberately grouped development sampling would
need revisiting for a large real source.

For the first real task, establish intended judgment and source authority,
inspect a real sample and references, confirm missing-label meaning and
pre-decision input availability, then select the adapter, method family, error
costs, and independent assessment split. Historical reproduction is the
explicit assumption for this fixture; a normative standard or outcome/action
objective needs different evidence and evaluation. Architecture implications
are limited to collecting required inputs, supplying references, and handling
abstentions.

## Implementation map

- `logic_foundry/data.py`: task/source/reference validation and profiling.
- `logic_foundry/discovery.py`: candidate counts, investigation, grouped method
  comparison, and artifact export.
- `logic_foundry/consumer.py`: standalone interpreter and integrity checks.
- `logic_foundry/evaluation.py`: held-out behavior, baselines, and diagnostics.
- `logic_foundry/reporting.py`, `__main__.py`: reports and CLI orchestration.
- `tests/`: meaningful behavior checks for label semantics, investigation,
  independent-group support, application, leakage prevention, reproducibility,
  and assessment metrics.
