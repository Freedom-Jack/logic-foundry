# Logic Foundry: research grounding

Prepared: October 13, 2026.

Scope note: CONCEPT.md revision 0.4 centers extraction and formalization of reusable logic. Workflow and architecture research below is supporting context for testing or applying artifacts, not the primary product scope.

This is a targeted review of primary research relevant to task investigation, system design, and reusable logic. It is not a market survey. No real project dataset or real-world artifact usefulness has been evaluated. The prototype's synthetic mechanics assessment is documented in README.md. The product implications below are inferences to test, not findings established for Logic Foundry.

## 1. Missing mappings and the observation process

[Learning Classifiers from Only Positive and Unlabeled Data — Elkan and Noto, 2008](https://cseweb.ucsd.edu/~elkan/posonly.pdf).

The paper distinguishes observed positive labels from underlying class membership: unlabeled examples can contain positives. Its probability correction relies on a particular random-labeling assumption.

Design implication: investigate whether an absent mapping means explicit rejection, missing annotation, or lack of exposure. Do not automatically treat absence as irrelevance. An estimated historical prior needs its own justification and should be distinguished from eligibility and decision costs.

Limit: the labeling assumption may fail in expert-selected histories. This paper neither determines the meaning of a missing business mapping nor justifies applying its correction automatically.

## 2. Information sufficiency and interpretation

[Sufficient Context: A New Lens on Retrieval Augmented Generation Systems — Joren et al., inspected arXiv v1, 2024](https://arxiv.org/html/2411.06037v1).

The study examines whether provided context supports answering separately from whether a model answers correctly. It reports failures with sufficient context and some correct answers with insufficient context.

Design implication: distinguish an information-access problem from an interpretation problem. Supplying curated evidence can help investigate a bottleneck before prescribing retrieval or model changes.

Limit: the experiments concern question answering and use an automatic context assessor. Their definition does not certify source truth, authority, or correct judgments in an arbitrary decision task.

## 3. Component diagnostics and complete-system behavior

[RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation — Ru et al., inspected arXiv v1, 2024](https://arxiv.org/html/2408.08067v1).

The framework combines final-answer measures with diagnostics of retrieval coverage, use of retrieved context, faithfulness, and noise sensitivity. It examines interactions between retrieved material and generator behavior.

Design implication: compare complete approaches while using component tests to investigate explanations. A candidate can retrieve related material yet still produce an inadequate result. Removing or substituting a component may reveal which design change is worth testing.

Limit: these text-task diagnostics do not establish correctness for every task or uniquely identify every failure cause. The authors also describe limitations in their retrieval diagnostics and treatment of contradictory versus neutral evidence.

## 4. Empirical selection among methods

[Auto-WEKA: Combined Selection and Hyperparameter Optimization of Classification Algorithms — Thornton et al., 2013](https://www.cs.ubc.ca/labs/algorithms/Projects/autoweka/papers/autoweka.pdf).

The work jointly searches supervised-learning algorithms, feature selection, and hyperparameters using empirical performance, then evaluates generalization separately.

Design implication: construct feasible candidates and compare them against an adequate target. Input format alone does not select a method. Search choices and assessment need distinct treatment.

Limit: the setting is supervised classification in WEKA. It assumes a usable target and search space; it does not solve tacit-knowledge elicitation, normative disagreement, inaccessible information, or general harness design.

## 5. Searching workflow structure

[AFlow: Automating Agentic Workflow Generation — Zhang et al., 2024](https://arxiv.org/abs/2410.10762).

The paper represents workflows in code and searches arrangements of LLM-invoking nodes using execution feedback. It evaluates those workflows on specified benchmarks.

Design implication: workflow structure can be included in candidate search when there are runnable alternatives, defined constraints, and an adequate evaluator. Logic Foundry could use small reference implementations to substantiate some design recommendations.

Limit: evidence from these benchmarks and operators does not establish universal architecture discovery, domain correctness, or successful deployment of arbitrary combinations of rules, retrieval, and numerical methods.

## Consequences for the redesign

The review supports investigating the chain from observation to task interpretation to candidate design. It does not provide a rule that maps a source type or pattern directly to an architecture.

The proposed product should:

- Establish what observations mean and what result is wanted.
- Investigate information dependencies before assuming a modeling failure.
- Compare feasible methods and designs within an explicit scope.
- Use diagnostic interventions alongside complete-system evaluation.
- Deliver runtime logic and its dependencies together with design guidance.
- Preserve what remains proposed, measured, or unresolved.

The next evidence needed is a real task walkthrough and candidate comparison. Research informs how to investigate; the task's data, objectives, and operating conditions must determine which approach is useful.
