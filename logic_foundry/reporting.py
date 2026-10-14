"""Small human-facing companions to the executable JSON and complete evidence log."""

from .data import canonical


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_discovery(artifact, evidence):
    inspection = evidence["profile"]
    investigation = evidence["investigation"]
    lines = ["# Extraction report", "", artifact["task"]["title"], "",
             "**Synthetic mechanics demonstration; real-data validation is pending.**" if artifact["task"]["synthetic"] else
             "Historical-agreement exploration using the supplied judgment authority.", "",
             "Target: `{}`. Authority: {}.".format(artifact["task"]["purpose"], artifact["task"]["judgment_authority"]), "",
             "Imported {} records in {} groups; {} are in scope. Judgment statuses: {}.".format(
                 inspection["records"], inspection["groups"], inspection["in_scope_count"], canonical(inspection["judgment_status_counts"])), "",
             evidence["method_choice"]["reason"], "",
             "## Development comparison", "",
             "Separate assessment cases are not read by discovery. All counts below are exploratory leave-one-group-out development results. "
             "Only resolved in-scope references enter these denominators. A correct set earns 1, an incorrect set costs {}, and abstention earns 0; "
             "these task settings are a selection heuristic, not an acceptance threshold.".format(artifact["selection"]["settings"]["incorrect_cost"]), "",
             "| Candidate | Correct | Incorrect | Abstained | Utility |", "| --- | ---: | ---: | ---: | ---: |"]
    for candidate in evidence["candidate_comparison"]:
        score = candidate["validation"]
        lines.append("| {} | {} | {} | {} | {} |".format(candidate["candidate_id"], score["correct"], score["incorrect"], score["abstained"], score["utility"]))
    lines += ["", "Selected `{}`; exported {} executable rules. The representation can also export zero rules when no cell is supported.".format(
        evidence["selected_candidate"], len(artifact["rules"])), "", "## Targeted investigation", "",
        "Action: `{}`. {}".format(investigation["action"], investigation["question"]), "",
        investigation["selection_reason"], "", "Effect: **{}**. {}".format(investigation["effect"], investigation["conclusion"])]
    details = investigation["evidence"]
    if investigation["action"] == "resolve_reference":
        lines += ["", "Reference `{}` (SHA-256 `{}`) resolved these observed alias groups:".format(details["reference_version"], details["reference_sha256"]), ""]
        lines += ["- {}: {}".format(topic, ", ".join(codes)) for topic, codes in details["observed_aliases_by_meaning"].items()]
        lines += ["", "Unresolved reference records: {}.".format(", ".join(details["unresolved_record_ids"]) or "none")]
    lines += ["", "## Selected claims and evidence", "",
        "A cell becomes executable only when its resolved judgments are unanimous and supported by at least {} distinct development groups. "
        "Unannotated/disputed judgments provide context only. A majority in a contradicted cell is a candidate claim, not an exported rule.".format(
            artifact["selection"]["settings"]["min_support"]), "",
        "| Conditions | Candidate target set | Status | Supporting IDs | Conflicting IDs | Unresolved IDs |",
        "| --- | --- | --- | --- | --- | --- |"]
    chosen = next(c for c in evidence["candidate_comparison"] if c["candidate_id"] == evidence["selected_candidate"])
    for claim in chosen["claims"]:
        lines.append("| {} | {} | {} | {} | {} | {} |".format(*[_cell(v) for v in (
            canonical(claim["conditions"]), canonical(claim["candidate_targets"]), claim["status"],
            ", ".join(claim["supporting_ids"]), ", ".join(claim["conflicting_ids"]), ", ".join(claim["unresolved_ids"]))]))
    lines += ["", "All candidate claims, fold counts, provenance hashes, and investigation evidence are in `evidence.json`. "
              "Record IDs refer to the original development collection; preserve that collection with this export.", "",
              "## Limits and next evidence", ""]
    lines += ["- " + limitation for limitation in artifact["limitations"]]
    lines += ["", "Before real use, obtain a real sample, confirm target authority and missing-label meaning, "
              "verify pre-decision availability and case groups, then choose the adapter, methods, metrics, and error costs for that task. "
              "This fixture does not settle those choices.", ""]
    return "\n".join(lines)


def render_application(artifact):
    lines = ["# Applying the exported artifact", "", "Artifact ID: `{}`".format(artifact["artifact_id"]), "",
             "Load `artifact.json` with `logic_foundry.consumer.Consumer.from_path`, then call `predict(inputs)`. "
             "No development source or evidence report is needed at runtime. The CLI `predict` command uses this same consumer.", "",
             "## Inputs and dependencies", "", "| Required input | Type | Meaning |", "| --- | --- | --- |"]
    for name, spec in sorted(artifact["input_requirements"].items()):
        lines.append("| {} | {} | {} |".format(name, spec["type"], _cell(spec.get("description", "Declared task input"))))
    scope = artifact["scope"]
    lines += ["", "Scope: `{}` must equal `{}`. {}".format(scope["field"], canonical(scope["equals"]), scope.get("description", ""))]
    reference = artifact.get("reference")
    if reference:
        lines += ["", "The artifact bundles codebook `{}` from {}. It resolves `{}` into `{}`. "
                  "Entries hash: `{}`. Updates require a new extraction and assessment; no live lookup occurs.".format(
                      reference["version"], reference["authority"], reference["input_field"], reference["resolved_field"], reference["entries_sha256"])]
    lines += ["", "## Runtime behavior", "",
              "Rules match the complete selected feature tuple exactly; there is no keyword inference, majority fallback, or hidden model. "
              "A `decided` result contains a complete `targets` list, matching rule IDs, and supporting development IDs. "
              "An empty list is an explicit no-route judgment. `abstain` contains `targets: null` and a reason; the receiver must handle that state.", "",
              "Missing/wrongly typed inputs, unknown reference codes, unseen values, unsupported combinations, outside-scope cases, "
              "and conflicted or insufficiently supported cells abstain. Additional inputs are ignored. "
              "Integrity hashes detect accidental changes; they do not authenticate an artifact's author.", "",
              "The receiving solution needs to collect the declared inputs, preserve reference meaning, and route abstentions for further evidence "
              "or review. Those requirements follow from the artifact; production workflow design is outside this prototype.", "",
              "## Output interpretation", "", artifact["task"]["label_semantics"]["resolved"], "",
              artifact["task"]["label_semantics"]["empty_targets"], "",
              "These decisions reproduce supported historical examples within scope. Their agreement does not establish an intended standard or better outcomes.", ""]
    if artifact["task"]["synthetic"]:
        lines += ["**Synthetic fixture only. Real-data validation is pending.**", ""]
    return "\n".join(lines)
