# Logic Foundry: product concept

Status: product direction for discussion; implementation starts with the bounded prototype in MVP.md.

Revision: 0.4 — extracting and formalizing reusable logic is the primary goal.

Prepared: October 8, 2026. Revised: October 13, 2026.

## Primary purpose

Logic Foundry extracts, develops, and formalizes reusable decision logic from available knowledge so that builders can use it in AI agents, algorithms, and other automated solutions.

Source knowledge can include historical cases and judgments, outcomes, written criteria, expert experience, conventions, objectives, and constraints. The primary deliverables are operational logic artifacts, accompanied by evidence and application information.

Investigation, method selection, and testing serve that goal. Findings can inform downstream system architecture, but general agent or harness design is not the product's primary responsibility. Builders use the artifacts and their information requirements to design or improve the receiving solution.

## The problem being addressed

Knowledge is often difficult to transfer into operational behavior. A historical collection may contain useful regularities, inconsistent judgments, missing context, and misleading associations. A written standard may be ambiguous. Experts may use distinctions that are absent from supplied records.

Extracting logic therefore involves more than summarizing documents or fitting historical labels. The agent must determine what information supports the task, investigate consequential uncertainty, choose appropriate analytical methods, and formalize the supported result.

The intent matters: reproducing a practice, applying an intended standard, predicting an outcome, and choosing an action require different targets and evidence. The agent should help establish that intent without requiring the user to supply a finished methodology.

A collection of 100,000 human complaint-to-section mappings is an illustrative source. Logic Foundry should help discover and formalize useful decision logic from such material. It should not assume the collection contains uniquely recoverable, complete, or correct rules. Distinct methods can agree on historical cases and behave differently on new ones.

## Meaning of logic and artifacts

**Logic** is the reusable method connecting relevant inputs to the intended judgment, estimate, or decision within a stated scope.

**A logic artifact** is a representation a receiving component can actually apply, with enough application information to preserve its meaning.

“Rules” is used broadly here as decision logic. It includes explicit conditions and exceptions where appropriate, and can also include numerical relationships, learned parameters, rubrics, examples, or instructions. This follows the original brief's consumer-dependent meaning; the product does not force every relationship into an explicit rule.

A numerical artifact needs feature meaning and transformations. A rubric needs usable criteria, input context, and output meaning. A reference-backed procedure needs its information source and missing-reference behavior made explicit.

Multiple artifacts can be complementary or alternatives. Associate them with their intended uses, dependencies, and compatibility assumptions. Their formats follow their consumers; there is no required universal artifact schema.

## Core responsibilities

### Understand the intended task and inspect the evidence

Identify what judgment is wanted, what the outputs mean, which inputs are available, and which errors matter. Inspect source quality, label meaning, repeated cases, available context, and relevant changes over time.

The user can begin with material and an objective. The agent should infer what it can and ask focused questions when purpose, authority, or inaccessible information materially changes the work.

### Discover candidate decision logic

Use suitable methods to surface useful relationships, criteria, distinctions, and exceptions. These can include statistical analysis, structural profiling, source inspection, expert elicitation, language interpretation, or combinations.

The investigative method does not predetermine the artifact format. Statistical analysis can support an explicit rule; expert elicitation can motivate a numerical feature; an LLM can coordinate work that ultimately produces a deterministic procedure.

Keep candidate interpretations linked to supporting and conflicting evidence. Do not automatically turn every correlation into a rule or every disagreement into noise.

### Investigate consequential uncertainty

Choose actions that could change the candidate logic or its applicability claim. Establish what is uncertain, which results would matter, what accessible evidence could distinguish explanations, and whether the investigation warrants its effort.

For an opaque identifier, investigate whether it encodes a convention, references another record, reflects an earlier decision, or carries a useful predictive association. A codebook, contrasting cases, record resolution, or targeted analysis may be appropriate.

For absent historical mappings, distinguish explicit rejection from missing annotation or lack of exposure. Unlabeled examples are not necessarily negative examples. [Elkan and Noto](https://cseweb.ucsd.edu/~elkan/posonly.pdf).

An inferred frequency prior may be useful under supported sampling and labeling assumptions. It does not automatically establish eligibility or justify overlooking rare important cases.

### Formalize usable artifacts

Express supported candidate logic in a form the intended component can apply. Include input meaning, dependencies, handling of unresolved cases, and relevant application instructions.

Artifacts should enable reuse without requiring a person to reinterpret the source knowledge for every case. Human explanations help users inspect and maintain the operational representation.

The agent can produce an exploratory artifact, a supported artifact within a narrower scope, or a specific information gap. It should not fabricate a complete rule set when the evidence is inadequate.

### Test behavior and revise

Apply artifacts through a simple reference consumer or an existing receiving system. Assess actual judgments on appropriate cases and investigate disagreements.

Separate development material from assessment material. Evaluate important case groups and error patterns rather than relying only on aggregate agreement. Preserve uncertainty in disputed reference judgments.

The evaluation claim should state the task, cases, consumer configuration, and limitations. Successful historical fit does not establish future reliability or that the historical practice was desirable.

For composed artifacts, evaluate the assembled behavior as well as individual parts. Component tests can help identify which assumptions or dependencies need further investigation.

## Primary outputs and downstream uses

| Output | Role |
| --- | --- |
| Reusable logic artifacts | Primary deliverable: rules, parameters, rubrics, mappings, procedures, or other operational representations |
| Supporting and conflicting evidence | Help assess why a candidate was chosen and where it is uncertain |
| Behavioral evaluation | Show observed usefulness and limitations through a specified consumer |
| Application requirements and explanation | Let builders integrate and maintain the artifacts |
| Architecture implications where relevant | Secondary guidance about capabilities the receiving solution may need |

The architecture use remains valuable. A discovered reference dependency may imply a resolver; distinct useful methods may motivate routing or composition; a rubric may require a particular input context. These implications follow from the extracted logic and its evidence. They do not require Logic Foundry to search arbitrary harness architectures.

The consumer can already exist or be under development. In the latter case, application requirements can help define its interface. The eventual integrated system still needs assessment.

## Users and product boundary

The working user hypothesis is a domain expert, analyst, or technical builder who has relevant knowledge and wants reusable logic for an automated task. People supply intent, contextual knowledge, and responsibility for consequential interpretation choices. The agent carries out and coordinates discovery, formalization, and testing.

Logic Foundry owns the knowledge-to-artifact process. Builders own downstream production solutions. Small consumers or experimental adapters belong inside the product when they are needed to evaluate artifacts; arbitrary production agent generation is outside the initial scope.

The value to test is whether users obtain useful, reusable logic with less repeated interpretation and fewer consequential errors, at an acceptable expert, analytical, and integration cost.

## Initial prototype

Build one complete extraction-and-formalization path for a bounded recurring judgment task and one source collection.

The prototype should inspect evidence, discover candidate logic, carry out useful targeted investigations, produce an operational artifact, and evaluate it through a reference consumer. Keep method selection open within a small supported repertoire.

Use the first real source sample to choose the input adapter and initial artifact representation. Historical mappings are a promising first source type, but the invented complaint example and record count do not establish an actual available dataset or a permanent domain restriction.

The initial prototype should demonstrate artifact reuse, beyond an analysis report. It does not need general architecture search, a universal artifact format, or a polished multi-user application.

The concrete scope and acceptance criteria are in [MVP.md](MVP.md).

## Important assumptions and remaining decisions

- Historical judgments are evidence; the intended target and their authority must be established.
- “Rules” retains the broad consumer-dependent meaning of decision logic from the original brief.
- No actual project dataset has been supplied or analyzed.
- The first input adapter and artifact representation need a sample or schema from one real task.
- Exact success metrics and acceptable error tradeoffs depend on that task.
- Investigation must be bounded by accessible sources, tools, and effort.
- Architecture guidance remains a downstream use of the primary artifacts and findings.

Prior proposed modes, Checks, agent-role structures, schemas, and lifecycles are optional ideas. They are not inherited requirements.

[RESEARCH.md](RESEARCH.md) provides relevant research grounding. Its workflow-design material is supporting context, not an expansion of the core product scope.
