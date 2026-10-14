"""Descriptive, held-out evaluation of an exported logic artifact.

This module never fits or changes an artifact. Unresolved references remain
visible but cannot become negative labels or contribute to agreement metrics.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .consumer import Consumer
from .data import canonical, case_fingerprint


def _targets(values: list[str]) -> list[str]:
    return sorted(set(values))


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _comparison(judgment: dict, decision: dict) -> str:
    if judgment["status"] != "resolved":
        return "unresolved_reference"
    if decision["status"] == "abstain":
        return "abstained"
    return (
        "correct"
        if _targets(judgment["targets"]) == _targets(decision["targets"])
        else "discrepancy"
    )


def _metrics(rows: list[dict], decision_key: str = "decision") -> dict:
    resolved = [row for row in rows if row["judgment"]["status"] == "resolved"]
    comparisons = [_comparison(row["judgment"], row[decision_key]) for row in resolved]
    correct = comparisons.count("correct")
    incorrect = comparisons.count("discrepancy")
    abstained = comparisons.count("abstained")
    covered = correct + incorrect
    return {
        "resolved_total": len(resolved),
        "correct": correct,
        "incorrect": incorrect,
        "abstained": abstained,
        "decided": covered,
        "exact_agreement": _ratio(correct, len(resolved)),
        "coverage": _ratio(covered, len(resolved)),
        "covered_exact_agreement": _ratio(correct, covered),
    }


def _per_target(rows: list[dict], target_ids: list[str], decision_key: str) -> dict:
    result = {}
    for target in sorted(target_ids):
        tp = fp = fn = abstained_positive = 0
        evaluated = 0
        for row in rows:
            if row["judgment"]["status"] != "resolved":
                continue
            expected = target in row["judgment"]["targets"]
            decision = row[decision_key]
            if decision["status"] == "abstain":
                abstained_positive += int(expected)
                continue
            evaluated += 1
            predicted = target in decision["targets"]
            tp += int(expected and predicted)
            fp += int(not expected and predicted)
            fn += int(expected and not predicted)
        result[target] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "evaluated_decisions": evaluated,
            "abstained_reference_positive": abstained_positive,
            "precision": _ratio(tp, tp + fp),
            "recall_among_decided": _ratio(tp, tp + fn),
        }
    return result


def _group_summary(rows: list[dict]) -> dict:
    metrics = _metrics(rows)
    baseline = _metrics(rows, "baseline")
    return {
        "n": metrics["resolved_total"],
        "record_count": len(rows),
        "unresolved_count": len(rows) - metrics["resolved_total"],
        "coverage": metrics["coverage"],
        "agreement": metrics["exact_agreement"],
        "covered_agreement": metrics["covered_exact_agreement"],
        "baseline_agreement": baseline["exact_agreement"],
        "baseline_coverage": baseline["coverage"],
        "correct": metrics["correct"],
        "incorrect": metrics["incorrect"],
        "abstained": metrics["abstained"],
    }


def _scope_groups(artifact: dict, records: list[dict], rows: list[dict]) -> dict:
    scope = artifact.get("scope")
    if scope is None:
        return {}
    grouped = {name: [] for name in ("in_scope", "outside_scope", "missing_scope")}
    rows_by_id = {row["id"]: row for row in rows}
    for record in records:
        value = record["inputs"].get(scope["field"])
        if value is None:
            name = "missing_scope"
        elif canonical(value) == canonical(scope["equals"]):
            name = "in_scope"
        else:
            name = "outside_scope"
        grouped[name].append(rows_by_id[record["id"]])
    return {name: _group_summary(members) for name, members in grouped.items()}


def _check_separation(artifact: dict, records: list[dict], digest: str) -> None:
    if not records:
        raise ValueError("Assessment requires at least one record.")
    if not isinstance(digest, str) or not digest:
        raise ValueError("Assessment SHA-256 must be supplied.")
    provenance = artifact["provenance"]
    if digest == provenance["development_sha256"]:
        raise ValueError("Assessment file is the development collection (same SHA-256).")
    checks = (
        ("record IDs", {row["id"] for row in records}, set(provenance["development_record_ids"])),
        ("case groups", {row["group_id"] for row in records}, set(provenance["development_group_ids"])),
        (
            "case fingerprints",
            {case_fingerprint(row) for row in records},
            set(provenance["development_case_fingerprints"]),
        ),
    )
    for name, assessment, development in checks:
        overlap = sorted(assessment & development)
        if overlap:
            raise ValueError(f"Assessment overlaps development {name}: {', '.join(overlap)}")
    ids = [row["id"] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Assessment record IDs must be unique.")


def evaluate(artifact: dict, records: list[dict], assessment_sha256: str) -> dict:
    """Apply a frozen artifact and its development baseline to separate cases.

    Headline agreement and coverage include all submitted resolved references,
    including outside-scope and missing-scope cases. Scope groups are also shown.
    Exact agreement counts an abstention as non-agreement. Undefined rates are
    ``None`` rather than a fabricated zero. Disputed allowed-set matches are
    diagnostics, never correctness labels.
    """
    _check_separation(artifact, records, assessment_sha256)
    consumer = Consumer(artifact)
    baseline_targets = _targets(artifact["baseline"]["targets"])
    rows: list[dict[str, Any]] = []
    diagnostics = []
    for record in sorted(records, key=lambda row: row["id"]):
        judgment = deepcopy(record["judgment"])
        decision = deepcopy(consumer.predict(record["inputs"]))
        baseline = {
            "status": "decided",
            "targets": list(baseline_targets),
            "reason": "Most frequent resolved target set in development records.",
        }
        row = {
            "id": record["id"],
            "group_id": record["group_id"],
            "tags": sorted(set(record.get("tags", []))),
            "judgment": judgment,
            "decision": decision,
            "baseline": baseline,
            "comparison": _comparison(judgment, decision),
            "baseline_comparison": _comparison(judgment, baseline),
        }
        if judgment["status"] == "disputed":
            allowed = sorted({_as_tuple(value) for value in judgment.get("acceptable_targets", [])})
            diagnostic = {
                "id": record["id"],
                "acceptable_targets": [list(value) for value in allowed],
                "decision_matches_allowed_set": (
                    _as_tuple(decision["targets"]) in allowed
                    if allowed and decision["status"] == "decided"
                    else None
                ),
                "note": "Allowed-set diagnostic only; disputed references have no correctness score.",
            }
            row["disputed_diagnostic"] = diagnostic
            diagnostics.append(diagnostic)
        rows.append(row)

    unresolved = [row for row in rows if row["comparison"] == "unresolved_reference"]
    counts = {
        status: sum(row["judgment"]["status"] == status for row in rows)
        for status in ("resolved", "unannotated", "disputed")
    }
    tag_names = sorted({tag for row in rows for tag in row["tags"]})
    target_ids = sorted(artifact["task"]["target_ids"])
    target_groups = {
        target: _group_summary([
            row for row in rows
            if row["judgment"]["status"] == "resolved" and target in row["judgment"]["targets"]
        ])
        for target in target_ids
    }
    # A resolved empty set is an explicit judgment, distinct from missing labels.
    no_target_group = _group_summary([
        row for row in rows
        if row["judgment"]["status"] == "resolved" and not row["judgment"]["targets"]
    ])
    limitations = list(artifact.get("limitations", []))
    if artifact["task"].get("synthetic"):
        limitations.append("Synthetic fixtures demonstrate mechanics only; real-data validation is pending.")
    limitations.extend([
        "This is descriptive agreement with supplied historical judgments, not evidence of an intended standard, improved outcomes, or future reliability.",
        "Disputed and unannotated references are excluded from correctness metrics.",
        "Headline metrics use the full submitted resolved collection, including outside-scope and missing-scope cases; automatic scope groups show bounded applicability separately.",
        "Exact agreement counts abstentions as non-agreement; covered agreement is conditional on a decision.",
        "Per-target confusion counts use decided cases with resolved references only; abstentions are reported separately.",
        "Group n is the number of resolved references; overlapping tags and multiple targets do not form disjoint partitions.",
    ])
    return {
        "schema_version": "1.0",
        "artifact_id": artifact["artifact_id"],
        "task": deepcopy(artifact["task"]),
        "consumer": "logic_foundry.consumer.Consumer",
        "assessment": {
            "sha256": assessment_sha256,
            "record_count": len(rows),
            "resolved_count": counts["resolved"],
            "unannotated_count": counts["unannotated"],
            "disputed_count": counts["disputed"],
            "overall_coverage": _ratio(sum(row["decision"]["status"] == "decided" for row in rows), len(rows)),
        },
        "metrics": _metrics(rows),
        "baseline": {
            "description": "Fixed development majority target set, applied to every assessment case.",
            "targets": baseline_targets,
            "metrics": _metrics(rows, "baseline"),
            "per_target": _per_target(rows, target_ids, "baseline"),
        },
        "per_target": _per_target(rows, target_ids, "decision"),
        "groups": {
            "scope": _scope_groups(artifact, records, rows),
            "tags": {tag: _group_summary([row for row in rows if tag in row["tags"]]) for tag in tag_names},
            "targets": target_groups,
            "empty_target_set": {"explicit empty judgment": no_target_group},
        },
        "rows": rows,
        "discrepancies": [row for row in rows if row["comparison"] == "discrepancy"],
        "abstentions": [row for row in rows if row["decision"]["status"] == "abstain"],
        "unresolved_references": {
            "counts": {status: counts[status] for status in ("unannotated", "disputed")},
            "rows": unresolved,
        },
        "disputed_diagnostics": diagnostics,
        "limitations": list(dict.fromkeys(limitations)),
    }


def _as_tuple(values: list[str]) -> tuple[str, ...]:
    return tuple(_targets(values))


def _rate(value: float | None) -> str:
    return "undefined (no cases)" if value is None else f"{value:.1%}"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_evaluation(report: dict) -> str:
    """Render a compact, reproducible Markdown view of the machine-readable report."""
    metrics = report["metrics"]
    baseline = report["baseline"]
    lines = [
        f"# Assessment: {_cell(report['task']['title'])}",
        "",
        f"Artifact: `{_cell(report['artifact_id'])}`. Assessment SHA-256: `{report['assessment']['sha256']}`.",
        "",
        f"Resolved references: {metrics['resolved_total']}; correct: {metrics['correct']}; "
        f"discrepancies: {metrics['incorrect']}; abstentions: {metrics['abstained']}.",
        "",
        "| Method | Exact agreement | Coverage | Agreement when decided |",
        "| --- | --- | --- | --- |",
        f"| Artifact | {_rate(metrics['exact_agreement'])} | {_rate(metrics['coverage'])} | {_rate(metrics['covered_exact_agreement'])} |",
        f"| Development majority | {_rate(baseline['metrics']['exact_agreement'])} | {_rate(baseline['metrics']['coverage'])} | {_rate(baseline['metrics']['covered_exact_agreement'])} |",
        "",
        "Headline agreement and coverage use all submitted cases with resolved references, including "
        "outside-scope and missing-scope cases. The baseline decides on the full submitted population. "
        "Abstentions count as non-agreement. "
        "A resolved empty target set is an explicit judgment.",
    ]
    in_scope = report["groups"].get("scope", {}).get("in_scope")
    if in_scope is not None:
        lines.extend([
            "",
            f"In-scope resolved references: {in_scope['n']}; exact agreement: {_rate(in_scope['agreement'])}; "
            f"coverage: {_rate(in_scope['coverage'])}; agreement when decided: {_rate(in_scope['covered_agreement'])}.",
        ])
    lines.extend([
        "",
        "## Case groups",
        "",
        "Group n counts resolved references. Tags and targets may overlap.",
        "",
        "| Group | n | Unresolved | Coverage | Agreement | Baseline agreement |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ])
    for kind, groups in report["groups"].items():
        for name, summary in groups.items():
            lines.append(
                f"| {_cell(kind)}: {_cell(name)} | {summary['n']} | {summary['unresolved_count']} | "
                f"{_rate(summary['coverage'])} | {_rate(summary['agreement'])} | {_rate(summary['baseline_agreement'])} |"
            )
    lines.extend([
        "", "## Assessment cases", "",
        "All rows are retained so discrepancies, abstentions, and unresolved references can be inspected.", "",
        "| ID | Reference status | Reference targets | Decision | Predicted targets | Comparison | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in report["rows"]:
        lines.append(
            f"| {_cell(row['id'])} | {row['judgment']['status']} | {_cell(row['judgment'].get('targets'))} | "
            f"{row['decision']['status']} | {_cell(row['decision'].get('targets'))} | "
            f"{row['comparison']} | {_cell(row['decision'].get('reason', ''))} |"
        )
    unresolved = report["unresolved_references"]["counts"]
    lines.extend([
        "", "## Unresolved references", "",
        f"Unannotated: {unresolved['unannotated']}; disputed: {unresolved['disputed']}. "
        "These rows have no correctness score.",
    ])
    for diagnostic in report["disputed_diagnostics"]:
        lines.extend([
            "",
            f"- {_cell(diagnostic['id'])}: allowed sets {diagnostic['acceptable_targets']}; "
            f"decision matches an allowed set: {diagnostic['decision_matches_allowed_set']}. Diagnostic only.",
        ])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines) + "\n"
