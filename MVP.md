# Logic Foundry: first prototype implementation brief

Status: implemented as a bounded local CLI using synthetic fixtures. See README.md for the workflow, outputs, checks, and limitations. Real-data validation is pending.

Prepared: October 13, 2026.

## Objective

Build a bounded prototype that turns a source collection into reusable decision logic, then demonstrates that logic through a reference consumer with supporting evidence.

Read CONCEPT.md revision 0.4 as the current product direction. Earlier architecture-centered framing is superseded: downstream architecture guidance is a possible consequence of the extracted logic, not the prototype's primary deliverable.

## First vertical slice

1. Accept one task description and one source collection.
2. Inspect the source and surface candidate relationships, criteria, and exceptions.
3. Let the agent choose and carry out a useful targeted investigation from a limited tool repertoire.
4. Formalize candidate logic in an operational representation.
5. Apply it through a reference consumer on separate assessment cases.
6. Export the artifact, application requirements, evidence, and observed limitations.

These describe the demonstration outcome. They do not mandate a fixed agent architecture or prevent returning to earlier questions during investigation.

## Input decisions needed first

Inspect a small sample or schema from one real task before choosing the concrete importer and artifact family. The 100,000 complaint-to-section mappings are illustrative; that dataset has not been supplied.

For a historical-mapping task, establish:

- The case inputs available when a new judgment must be made.
- The meaning of target IDs and whether a case can have multiple, no, or unresolved mappings.
- Relevant reference material and versions, where needed to interpret those IDs.
- Whether historical judgments are authoritative targets, provisional examples, or evidence alongside a separate intended standard.
- Available timestamps, grouping identifiers, and context useful for assessment.

Only fields necessary for the chosen task should become required inputs. Do not invent a universal complaint schema.

## Discovery and formalization

Start with a small analytical repertoire sufficient to investigate meaningful alternatives. Candidate capabilities include source profiling, conditional counts and association analysis, contrasting-case inspection, focused expert questions, and source-grounded language interpretation.

Choose methods from the task and evidence. Do not require a rubric merely because inputs contain text, or a statistical predictor merely because identifiers show a pattern. Keep candidate claims connected to supporting and conflicting cases or source passages.

The first artifact family should be chosen after inspecting the sample and identifying how it can be applied. It could be explicit decision rules, a numerical method, a rubric, or a bounded composition. Support one useful family well before adding arbitrary formats.

Every exported artifact needs a usable representation and application information. An explanation or list of suggested rules without a way to apply it is insufficient.

## Evaluation and acceptance

The prototype is demonstrated when:

- A source collection can be imported and inspected reproducibly.
- A candidate logic claim is traceable to supporting and conflicting evidence.
- A targeted investigation produces recorded evidence that confirms, changes, or limits that claim.
- An exported artifact can be applied to a new case by the reference consumer without a person rewriting its meaning.
- Separate assessment cases yield reproducible results, with discrepancies and unresolved reference judgments visible.
- The report distinguishes historical agreement from claims about an intended standard or outcome improvement.
- The artifact's input requirements, information dependencies, and scope limits are recorded.

Set task-specific metrics after inspecting the sample and agreeing on the target. Compare against a simple relevant baseline. Do not invent a passing accuracy threshold or claim real-world reliability from a synthetic fixture.

Protect assessment material from adaptive artifact development. Use appropriate time or case grouping where repeated or related records would otherwise leak across the comparison.

## Practical boundaries

Prioritize the extraction and evaluation path over interface polish. Select a language, libraries, and packaging once the first data and consumer needs are known. A simple command-line workflow or small local interface is sufficient for the first demonstration.

If the real collection is large, use feasible full-collection profiling and deliberately selected cases for detailed investigation; preserve important rare and disputed cases. Do not assume each record requires an LLM call.

If real data is not yet available, synthetic fixtures can test ingestion, tool execution, artifact application, and evaluation mechanics. They do not validate the discovery method for the intended real task.

General harness generation, broad architecture search, production deployment, and universal artifact conversion are outside this prototype's scope. Small experimental consumers and adapters are included where needed to establish artifact usability.

## Implementation chat handoff

Start implementation from this brief and CONCEPT.md revision 0.4. Preserve the core goal: discover and formalize reusable logic from available knowledge so it can be used in downstream automated solutions.

The first action is to inspect the real source sample or schema, establish the judgment target, and choose the first operational artifact representation. Then implement the complete path above without expanding into general AI-system design.

Keeping the scope and completion criteria in project files follows the durable-context practice described in [official OpenAI guidance for longer coding tasks](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex).
