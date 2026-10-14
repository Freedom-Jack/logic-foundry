"""Strict adapter for this prototype's categorical historical-routing collection."""

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_value(value, kind):
    if kind == "boolean":
        return isinstance(value, bool)
    return isinstance(value, str) and bool(value.strip())


def validate_task(task):
    _require(isinstance(task, dict) and task.get("schema_version") == 1, "Task requires schema_version 1")
    for key in ("task_id", "title", "judgment_authority"):
        _require(isinstance(task.get(key), str) and bool(task[key].strip()), "Task requires " + key)
    _require(isinstance(task.get("synthetic"), bool), "Task must explicitly declare synthetic true/false")
    _require(task.get("purpose") == "historical_judgment_reproduction",
             "This adapter supports historical_judgment_reproduction only")
    targets = task.get("target_ids")
    _require(isinstance(targets, list) and bool(targets) and all(isinstance(t, str) and t for t in targets)
             and len(set(targets)) == len(targets), "target_ids must be unique nonempty strings")
    fields = task.get("input_fields")
    _require(isinstance(fields, dict) and 1 <= len(fields) <= 8, "Declare 1–8 categorical/boolean input fields")
    for name, spec in fields.items():
        _require(isinstance(name, str) and isinstance(spec, dict), "Invalid input field declaration")
        _require(spec.get("type") in ("categorical", "boolean"), "Unsupported field type: " + name)
        _require(isinstance(spec.get("available_at_decision"), bool), "Declare availability for " + name)
    scope = task.get("scope")
    _require(isinstance(scope, dict) and scope.get("field") in fields and "equals" in scope,
             "Declare a bounded scope with field and equals")
    _require(fields[scope["field"]]["available_at_decision"], "Scope input must be available at decision time")
    _require(valid_value(scope["equals"], fields[scope["field"]]["type"]), "Invalid scope value")
    semantics = task.get("label_semantics", {})
    _require(isinstance(semantics, dict), "label_semantics must be an object")
    _require(all(isinstance(semantics.get(k), str) and semantics[k] for k in
                 ("resolved", "unannotated", "disputed", "empty_targets")), "Declare label semantics including empty_targets")
    settings = task.get("discovery", {})
    _require(isinstance(settings, dict), "discovery must be an object")
    _require(type(settings.get("min_support")) is int and settings["min_support"] >= 2,
             "discovery.min_support must be an integer >= 2")
    _require(type(settings.get("max_rule_width")) is int and settings["max_rule_width"] in (1, 2),
             "discovery.max_rule_width must be 1 or 2")
    _require(type(settings.get("incorrect_cost")) in (int, float) and 0 < settings["incorrect_cost"] <= 1000,
             "discovery.incorrect_cost must be positive and finite (<= 1000)")
    reference = task.get("reference")
    if reference is not None:
        _require(isinstance(reference, dict) and isinstance(reference.get("path"), str)
                 and isinstance(reference.get("version"), str), "Reference needs path and version")
    return task


def load_task(path):
    return validate_task(read_json(path))


def validate_targets(targets, target_ids):
    _require(isinstance(targets, list) and all(isinstance(t, str) and t in target_ids for t in targets),
             "Targets must be a list of declared target IDs (empty means explicit no-target judgment)")
    _require(len(set(targets)) == len(targets), "Duplicate target IDs")
    return sorted(targets)


def validate_records(records, task):
    _require(isinstance(records, list) and bool(records), "Collection must contain at least one record")
    seen = set()
    for record in records:
        _require(isinstance(record, dict), "Each record must be an object")
        for key in ("id", "group_id", "observed_at"):
            _require(isinstance(record.get(key), str) and bool(record[key].strip()), "Record requires " + key)
        _require(record["id"] not in seen, "Duplicate record ID: " + record["id"])
        seen.add(record["id"])
        try:
            timestamp = datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00"))
            _require(timestamp.tzinfo is not None, "observed_at must include a timezone")
        except ValueError as error:
            raise ValueError("Invalid observed_at for " + record["id"] + ": " + str(error)) from error
        inputs = record.get("inputs")
        _require(isinstance(inputs, dict), "Record requires inputs object")
        _require(not set(inputs) - set(task["input_fields"]), "Undeclared input field in " + record["id"])
        for name, value in inputs.items():
            _require(value is None or valid_value(value, task["input_fields"][name]["type"]),
                     "Invalid input type for " + name + " in " + record["id"])
        judgment = record.get("judgment")
        _require(isinstance(judgment, dict), "Record requires judgment object")
        status = judgment.get("status")
        _require(status in ("resolved", "unannotated", "disputed"), "Invalid judgment status")
        if status == "resolved":
            judgment["targets"] = validate_targets(judgment.get("targets"), task["target_ids"])
            _require("acceptable_targets" not in judgment, "Resolved judgments cannot carry disputed alternatives")
        else:
            _require("targets" in judgment and judgment["targets"] is None, "Unresolved targets must be explicitly null")
            if "acceptable_targets" in judgment:
                _require(status == "disputed" and isinstance(judgment["acceptable_targets"], list)
                         and bool(judgment["acceptable_targets"]), "Only disputed judgments may list acceptable_targets")
                judgment["acceptable_targets"] = [validate_targets(t, task["target_ids"])
                                                    for t in judgment["acceptable_targets"]]
        _require(isinstance(record.get("tags", []), list) and
                 all(isinstance(t, str) for t in record.get("tags", [])), "tags must be a string list")
    return records


def load_records(path, task):
    records = []
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError("Invalid JSON at line {}: {}".format(number, error.msg)) from error
    return validate_records(records, task)


def validate_reference(reference, task):
    _require(isinstance(reference, dict) and reference.get("schema_version") == 1, "Codebook requires schema_version 1")
    _require(reference.get("version") == task["reference"]["version"], "Codebook version does not match task")
    source = reference.get("input_field")
    resolved = reference.get("resolved_field")
    _require(source in task["input_fields"] and task["input_fields"][source]["type"] == "categorical"
             and task["input_fields"][source]["available_at_decision"], "Codebook key must be an available categorical input")
    _require(isinstance(resolved, str) and bool(resolved) and resolved not in task["input_fields"],
             "Codebook needs a distinct resolved_field")
    _require(reference.get("available_at_decision") is True and isinstance(reference.get("authority"), str),
             "Codebook must declare pre-decision availability and authority")
    entries = reference.get("entries")
    _require(isinstance(entries, dict) and bool(entries), "Codebook entries must be nonempty")
    for key, entry in entries.items():
        _require(isinstance(key, str) and key and isinstance(entry, dict), "Invalid codebook entry")
        _require(set(entry) <= {resolved, "description"} and valid_value(entry.get(resolved), "categorical"),
                 "Codebook entries may contain predictor semantics and description only")
    return reference


def load_reference(task, task_path):
    if task.get("reference") is None:
        return None, None
    path = Path(task_path).parent / task["reference"]["path"]
    return validate_reference(read_json(path), task), file_sha256(path)


def in_scope(record, task):
    scope = task["scope"]
    return record["inputs"].get(scope["field"]) == scope["equals"]


def case_fingerprint(record):
    """Catch exact repeated observations even if a case/group identifier was renamed."""
    instant = datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00"))
    return digest({"observed_at": instant.timestamp(), "inputs": record["inputs"]})


def profile(records, task):
    fields = {}
    for name in task["input_fields"]:
        counts = Counter(canonical(r["inputs"][name]) for r in records if r["inputs"].get(name) is not None)
        fields[name] = {"missing_count": sum(r["inputs"].get(name) is None for r in records),
                        "distinct_values": len(counts), "counts": dict(sorted(counts.items()))}
    groups = Counter(r["group_id"] for r in records)
    resolved = [r for r in records if r["judgment"]["status"] == "resolved"]
    instants = [datetime.fromisoformat(r["observed_at"].replace("Z", "+00:00")).astimezone(timezone.utc) for r in records]
    return {"records": len(records), "groups": len(groups), "repeated_groups": {g: n for g, n in sorted(groups.items()) if n > 1},
            "judgment_status_counts": dict(sorted(Counter(r["judgment"]["status"] for r in records).items())),
            "resolved_target_sets": dict(sorted(Counter(canonical(r["judgment"]["targets"]) for r in resolved).items())),
            "in_scope_count": sum(in_scope(r, task) for r in records),
            "observed_at_range": [min(instants).isoformat(), max(instants).isoformat()],
            "fields": fields,
            "warnings": ["Label absence is not a negative judgment.",
                         "Declared pre-decision availability and group IDs require domain verification.",
                         "Synthetic fixtures test mechanics; real-data validation is pending."] if task["synthetic"] else
                        ["Historical judgments have the declared authority only; no normative validity is inferred."]}
