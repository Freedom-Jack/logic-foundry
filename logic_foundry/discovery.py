"""Bounded discovery: conditional counts, one targeted investigation, grouped validation."""

from collections import Counter, defaultdict
from itertools import combinations

from .consumer import Consumer, seal_artifact
from .data import canonical, case_fingerprint, digest, in_scope, profile


def _values(record, reference):
    values = dict(record["inputs"])
    if reference:
        entry = reference["entries"].get(values.get(reference["input_field"]))
        values[reference["resolved_field"]] = entry.get(reference["resolved_field"]) if entry else None
    return values


def _key(values, features):
    if any(values.get(f) is None for f in features):
        return None
    return canonical({f: values[f] for f in features})


def _table(records, features, min_support, reference):
    """Unanimous, repeated resolved cells become rules. Every other cell stays visible."""
    cells = defaultdict(list)
    domains = {f: {} for f in features}
    for record in records:
        values = _values(record, reference)
        key = _key(values, features)
        if key is None:
            continue
        cells[key].append(record)
        for f in features:
            domains[f][canonical(values[f])] = values[f]
    import json
    claims = []
    for key, rows in sorted(cells.items()):
        resolved = [r for r in rows if r["judgment"]["status"] == "resolved"]
        counts = Counter(canonical(r["judgment"]["targets"]) for r in resolved)
        majority = min(counts, key=lambda t: (-counts[t], t)) if counts else None
        supporting = [r["id"] for r in resolved if canonical(r["judgment"]["targets"]) == majority]
        conflicting = [r["id"] for r in resolved if canonical(r["judgment"]["targets"]) != majority]
        status = ("no_resolved_evidence" if not counts else "conflicted_evidence" if len(counts) > 1 else
                  "insufficient_support" if len(resolved) < min_support else "supported")
        claims.append({"claim_id": "claim-" + digest({"features": features, "conditions": json.loads(key)})[:12],
                       "conditions": json.loads(key), "candidate_targets": json.loads(majority) if majority else None,
                       "status": status, "supporting_ids": sorted(supporting), "conflicting_ids": sorted(conflicting),
                       "observed_ids": sorted(r["id"] for r in rows),
                       "unresolved_ids": sorted(r["id"] for r in rows if r["judgment"]["status"] != "resolved"),
                       "resolved_count": len(resolved), "support_count": len(supporting),
                       "support_group_count": len({r["group_id"] for r in resolved
                                                   if canonical(r["judgment"]["targets"]) == majority}),
                       "target_counts": dict(sorted(counts.items()))})
    # Support is counted by independent groups, not repeated records from one case family.
    for claim in claims:
        if claim["status"] == "supported" and claim["support_group_count"] < min_support:
            claim["status"] = "insufficient_support"
    rules = [{"rule_id": "rule-" + c["claim_id"][6:], "conditions": c["conditions"],
              "targets": c["candidate_targets"], "supporting_ids": c["supporting_ids"],
              "support_count": c["support_count"], "support_group_count": c["support_group_count"],
              "claim_id": c["claim_id"]} for c in claims if c["status"] == "supported"]
    return {"rules": rules, "claims": claims,
            "domains": {f: [v for _, v in sorted(items.items())] for f, items in domains.items()}}


def _table_predict(table, record, features, reference):
    key = _key(_values(record, reference), features)
    for rule in table["rules"]:
        if canonical(rule["conditions"]) == key:
            return rule["targets"]
    return None


def _candidate(records, features, task, reference, name):
    settings = task["discovery"]
    groups = sorted({r["group_id"] for r in records})
    counts = {"correct": 0, "incorrect": 0, "abstained": 0}
    folds = []
    for group in groups:
        train = [r for r in records if r["group_id"] != group]
        heldout = [r for r in records if r["group_id"] == group and r["judgment"]["status"] == "resolved"]
        if not heldout:
            continue
        table = _table(train, features, settings["min_support"], reference)
        fold = {"heldout_group": group, "heldout_ids": [r["id"] for r in heldout],
                "correct": 0, "incorrect": 0, "abstained": 0}
        for record in heldout:
            predicted = _table_predict(table, record, features, reference)
            outcome = "abstained" if predicted is None else "correct" if predicted == record["judgment"]["targets"] else "incorrect"
            counts[outcome] += 1
            fold[outcome] += 1
        folds.append(fold)
    total = sum(counts.values())
    score = counts["correct"] - settings["incorrect_cost"] * counts["incorrect"]
    table = _table(records, features, settings["min_support"], reference)
    return {"candidate_id": name + ":" + "+".join(features), "features": list(features),
            "uses_reference": reference is not None, "validation": {"method": "leave_one_group_out",
            "resolved_count": total, **counts, "utility": score,
            "agreement": counts["correct"] / total if total else None,
            "coverage": (total - counts["abstained"]) / total if total else None, "folds": folds},
            "claims": table["claims"], "rule_count": len(table["rules"]), "table": table}


def _rank(candidate):
    score = candidate["validation"]
    return (-score["utility"], score["incorrect"], -score["correct"], len(candidate["features"]),
            candidate["rule_count"], candidate["candidate_id"])


def discover(task, records, source_sha256, task_sha256, reference=None, reference_sha256=None):
    """Receives development records only. Assessment data is deliberately not an argument."""
    inspection = profile(records, task)
    scoped = [r for r in records if in_scope(r, task)]
    resolved = [r for r in scoped if r["judgment"]["status"] == "resolved"]
    if not resolved:
        raise ValueError("No resolved in-scope development judgments; cannot discover historical logic")
    if len({r["group_id"] for r in resolved}) < 2:
        raise ValueError("At least two independent resolved groups are required for development comparison")
    fields = sorted(f for f, spec in task["input_fields"].items()
                    if spec["available_at_decision"] and f != task["scope"]["field"])
    if not fields:
        raise ValueError("No available non-scope fields for discovery")
    candidates = []
    for width in range(1, min(task["discovery"]["max_rule_width"], len(fields)) + 1):
        for features in combinations(fields, width):
            candidates.append(_candidate(scoped, features, task, None, "raw"))
    best_raw = min(candidates, key=_rank)
    investigation = None
    if reference:
        source_field, semantic_field = reference["input_field"], reference["resolved_field"]
        observed_codes = sorted({r["inputs"][source_field] for r in scoped if r["inputs"].get(source_field) is not None})
        if len(observed_codes) >= 2:
            aliases = defaultdict(list)
            unresolved_ids = []
            for record in scoped:
                code = record["inputs"].get(source_field)
                entry = reference["entries"].get(code)
                if entry:
                    aliases[entry[semantic_field]].append(code)
                else:
                    unresolved_ids.append(record["id"])
            related_fields = [f for f in fields if f != source_field]
            feature_sets = [(semantic_field,)]
            if task["discovery"]["max_rule_width"] >= 2:
                feature_sets += [tuple(sorted((semantic_field, f))) for f in related_fields]
            for features in feature_sets:
                candidates.append(_candidate(scoped, features, task, reference, "resolved"))
            best_resolved = min((c for c in candidates if c["uses_reference"]), key=_rank)
            shared = {f: sorted(set(v)) for f, v in aliases.items() if len(set(v)) > 1}
            resolution_finding = ("The declared reference supplies predictor categories shared by distinct observed IDs." if shared else
                                  "The declared reference resolves observed IDs, but no shared meaning across distinct observed IDs was established." if aliases else
                                  "The declared reference resolves none of the observed IDs; it supplies no applicable input meaning for these records.")
            investigation = {"action": "resolve_reference", "budget": {"max_investigations": 1, "executed": 1},
                "question": "Do IDs in '{}' identify reusable pre-decision categories or only exact historical associations?".format(source_field),
                "selection_reason": "Multiple observed categorical IDs have a declared, available versioned codebook; resolving it can distinguish alias-specific associations from reusable input meaning.",
                "candidate_before": best_raw["candidate_id"],
                "alternatives_considered": ["Resolve declared codebook", "Inspect a conflicting cell using contrasting cases"],
                "evidence": {"reference_version": reference["version"], "reference_authority": reference["authority"],
                    "reference_sha256": reference_sha256,
                    "observed_aliases_by_meaning": {f: sorted(set(v)) for f, v in sorted(aliases.items())},
                    "unresolved_record_ids": sorted(unresolved_ids), "observed_codes": observed_codes,
                    "raw_candidate": {"id": best_raw["candidate_id"], "validation": best_raw["validation"]},
                    "resolved_candidate": {"id": best_resolved["candidate_id"], "validation": best_resolved["validation"]}},
                "conclusion": resolution_finding + " Exact-ID associations alone do not establish reusable semantics; unknown IDs remain unresolved. Comparison is development-only.",
                "candidate_after": best_resolved["candidate_id"],
                "effect": "changed" if _rank(best_resolved) < _rank(best_raw) else "limited",
                "limits": ["Pre-decision availability and taxonomy authority are declared, not independently established.",
                           "A codebook category is an input meaning, not a target decision or an intended standard."]}
    if investigation is None:
        conflicts = [cell for c in candidates for cell in c["claims"] if cell["conflicting_ids"]]
        conflicts.sort(key=lambda c: (-len(c["conflicting_ids"]), c["claim_id"]))
        supported = sorted((c for c in best_raw["claims"] if c["status"] == "supported"), key=lambda c: (-c["support_group_count"], c["claim_id"]))
        selected = conflicts[0] if conflicts else supported[0] if supported else best_raw["claims"][0] if best_raw["claims"] else None
        confirmed = selected is not None and selected["status"] == "supported"
        ids = (selected["supporting_ids"][:2] + selected["conflicting_ids"][:1]) if selected else []
        contrasting = [r for r in scoped if r["id"] in ids]
        investigation = {"action": "inspect_contrasting_cases", "budget": {"max_investigations": 1, "executed": 1},
            "question": "Do similar observed inputs support a unique historical judgment?",
            "selection_reason": "No usable multi-ID reference investigation; inspect the strongest observed contradiction, or a supported cell if no contradiction exists.",
            "evidence": {"claim": selected, "cases": contrasting}, "effect": "confirmed" if confirmed else "limited",
            "conclusion": "Conflicting resolved judgments block rule export; absent labels provide no negative evidence." if conflicts else
                          "Observed repeated cases support this bounded association; no authority or causal validity is inferred." if confirmed else
                          "No supported repeated association was established in the inspected cell; insufficient or missing evidence cannot confirm a reusable rule.",
            "limits": ["Record comparison cannot recover missing context or establish which historical judgment is correct."]}
    ranked = sorted(candidates, key=_rank)
    chosen = ranked[0]
    table = chosen["table"]
    used_reference = reference if chosen["uses_reference"] else None
    requirements = {f: task["input_fields"][f] for f in chosen["features"] if f in task["input_fields"]}
    requirements[task["scope"]["field"]] = task["input_fields"][task["scope"]["field"]]
    bundled_reference = None
    if used_reference:
        requirements[reference["input_field"]] = task["input_fields"][reference["input_field"]]
        bundled_reference = {**reference, "entries_sha256": digest(reference["entries"]), "source_sha256": reference_sha256}
    target_counts = Counter(canonical(r["judgment"]["targets"]) for r in resolved)
    majority = min(target_counts, key=lambda t: (-target_counts[t], t))
    import json
    limitations = ["Descriptive reproduction of resolved historical judgments; no intended-standard correctness, causal effect, or outcome improvement is established.",
                   "Only declared categorical/boolean inputs and conjunctions of at most two fields are supported.",
                   "Discovery and model selection reuse development groups; development scores are exploratory, not final assessment.",
                   "Unanimity and minimum independent-group support are conservative heuristics, not statistical confidence bounds.",
                   "Missing/disputed judgments are not negatives. Conflicted, rare, missing, unknown, and outside-scope cases may abstain.",
                   "Group IDs and information availability are supplied assumptions; renamed/non-identical related records may evade leakage checks.",
                   "Leave-one-group-out comparison measures reuse across declared groups, not robustness to future temporal drift."]
    if task["synthetic"]:
        limitations.insert(0, "SYNTHETIC MECHANICS DEMONSTRATION ONLY. Real-data validation and real-task method suitability are pending.")
    artifact = seal_artifact({"schema_version": 1, "artifact_family": "categorical_rule_table",
        "task": {k: task[k] for k in ("task_id", "title", "purpose", "judgment_authority", "synthetic", "target_ids", "label_semantics")},
        "scope": task["scope"], "record_schema": task["input_fields"],
        "features": chosen["features"], "feature_domains": table["domains"],
        "input_requirements": requirements, "reference": bundled_reference, "rules": table["rules"],
        "blocked_cells": [c for c in table["claims"] if c["status"] != "supported"],
        "baseline": {"method": "in_scope_development_majority_target_set", "targets": json.loads(majority),
                     "support_count": target_counts[majority], "resolved_count": len(resolved), "tie_break": "canonical JSON lexical order"},
        "selection": {"candidate_id": chosen["candidate_id"], "settings": task["discovery"],
                      "criterion": "correct - incorrect_cost * incorrect; abstention=0; ties: fewer errors, more correct, fewer fields, fewer rules, candidate ID",
                      "development_validation": chosen["validation"]},
        "provenance": {"development_sha256": source_sha256, "task_sha256": task_sha256, "codebook_sha256": reference_sha256,
                       "development_record_ids": sorted(r["id"] for r in records),
                       "development_group_ids": sorted({r["group_id"] for r in records}),
                       "development_case_fingerprints": sorted({case_fingerprint(r) for r in records})},
        "limitations": limitations})
    # Validate the actual operational representation, not just the discovery table.
    Consumer(artifact)
    evidence = {"schema_version": 1, "task_id": task["task_id"], "synthetic": task["synthetic"],
        "source_sha256": source_sha256, "profile": inspection,
        "method_choice": {"family": "categorical_rule_table",
            "reason": "The inspected adapter exposes finite categorical/boolean inputs and explicit target sets. Small conditional tables are directly executable and preserve contradictions; this demonstration does not establish suitability for a real task.",
            "alternatives": ["Raw-field conditional tables", "Codebook-resolved conditional tables when an available reference warrants investigation"],
            "not_tested": ["Free-text interpretation", "Numerical relationships", "LLM induction", "Intended-standard adjudication"]},
        "investigation": investigation, "selected_candidate": chosen["candidate_id"],
        "candidate_comparison": [{k: v for k, v in c.items() if k != "table"} for c in ranked],
        "limitations": limitations}
    return artifact, evidence
