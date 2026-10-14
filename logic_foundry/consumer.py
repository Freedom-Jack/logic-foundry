"""Standalone interpreter: exported JSON is sufficient; development data is not read."""

from .data import canonical, digest, read_json, valid_value, validate_targets


def seal_artifact(artifact):
    artifact = dict(artifact)
    artifact.pop("artifact_id", None)
    artifact["artifact_id"] = digest(artifact)
    return artifact


class Consumer:
    def __init__(self, artifact):
        if not isinstance(artifact, dict) or artifact.get("schema_version") != 1:
            raise ValueError("Unsupported artifact schema_version")
        if artifact.get("artifact_family") != "categorical_rule_table":
            raise ValueError("Unsupported artifact family")
        if seal_artifact(artifact)["artifact_id"] != artifact.get("artifact_id"):
            raise ValueError("Artifact integrity check failed; use an unchanged exported artifact")
        try:
            features = artifact["features"]
            if not features or len(set(features)) != len(features):
                raise ValueError("Artifact requires unique features")
            requirements = artifact["input_requirements"]
            for field, spec in requirements.items():
                if spec["type"] not in ("boolean", "categorical"):
                    raise ValueError("Invalid artifact input type: " + field)
            scope = artifact["scope"]
            if scope["field"] not in requirements or not valid_value(scope["equals"], requirements[scope["field"]]["type"]):
                raise ValueError("Invalid artifact scope")
            reference = artifact.get("reference")
            if reference:
                if reference["available_at_decision"] is not True or reference["input_field"] not in requirements:
                    raise ValueError("Invalid reference dependency")
                if digest(reference["entries"]) != reference["entries_sha256"]:
                    raise ValueError("Bundled reference integrity check failed")
            available = set(requirements)
            if reference:
                available.add(reference["resolved_field"])
            if not set(features) <= available:
                raise ValueError("Artifact features lack input dependencies")
            for feature in features:
                if not isinstance(artifact["feature_domains"].get(feature), list):
                    raise ValueError("Missing feature domain: " + feature)
            rule_ids = set()
            for rule in artifact["rules"]:
                if rule["rule_id"] in rule_ids or set(rule["conditions"]) != set(features):
                    raise ValueError("Invalid rule ID or conditions")
                rule_ids.add(rule["rule_id"])
                validate_targets(rule["targets"], artifact["task"]["target_ids"])
                if any(not self._contains(artifact["feature_domains"][f], value) for f, value in rule["conditions"].items()):
                    raise ValueError("Rule condition outside feature domain")
            validate_targets(artifact["baseline"]["targets"], artifact["task"]["target_ids"])
        except (KeyError, TypeError, AttributeError) as error:
            raise ValueError("Malformed artifact: " + str(error)) from error
        self.artifact = artifact

    @classmethod
    def from_path(cls, path):
        return cls(read_json(path))

    @staticmethod
    def _contains(values, value):
        # Python considers False == 0; canonical equality preserves JSON types.
        return any(canonical(v) == canonical(value) for v in values)

    def predict(self, inputs):
        artifact = self.artifact

        def result(status, reason, targets=None, rules=(), **extra):
            return {"status": status, "targets": targets, "reason": reason,
                    "matched_rule_ids": [r["rule_id"] for r in rules],
                    "evidence_ids": sorted({i for r in rules for i in r.get("supporting_ids", [])}),
                    "artifact_id": artifact["artifact_id"], **extra}

        if not isinstance(inputs, dict):
            return result("abstain", "invalid_inputs")
        scope = artifact["scope"]
        # Check scope first: outside-scope cases have no supported applicability claim.
        if inputs.get(scope["field"]) is None:
            return result("abstain", "missing_input", missing_inputs=[scope["field"]])
        if not valid_value(inputs[scope["field"]], artifact["input_requirements"][scope["field"]]["type"]):
            return result("abstain", "invalid_input_type", field=scope["field"])
        if canonical(inputs[scope["field"]]) != canonical(scope["equals"]):
            return result("abstain", "outside_scope")
        missing = sorted(f for f in artifact["input_requirements"] if inputs.get(f) is None)
        if missing:
            return result("abstain", "missing_input", missing_inputs=missing)
        for field, spec in artifact["input_requirements"].items():
            if not valid_value(inputs[field], spec["type"]):
                return result("abstain", "invalid_input_type", field=field)
        values = dict(inputs)
        reference = artifact.get("reference")
        if reference:
            code = values[reference["input_field"]]
            entry = reference["entries"].get(code)
            if entry is None:
                return result("abstain", "unresolved_reference", field=reference["input_field"], value=code,
                              reference_version=reference["version"])
            values[reference["resolved_field"]] = entry[reference["resolved_field"]]
        for feature in artifact["features"]:
            if not self._contains(artifact["feature_domains"][feature], values[feature]):
                return result("abstain", "unseen_feature_value", field=feature, value=values[feature])
        matched = [r for r in artifact["rules"]
                   if all(canonical(values[f]) == canonical(v) for f, v in r["conditions"].items())]
        if matched:
            outputs = {canonical(r["targets"]) for r in matched}
            if len(outputs) != 1:
                return result("abstain", "conflicting_rules", rules=matched)
            return result("decided", "supported_rule", list(matched[0]["targets"]), matched)
        blocked = [cell for cell in artifact.get("blocked_cells", [])
                   if all(canonical(values[f]) == canonical(v) for f, v in cell["conditions"].items())]
        if blocked:
            return result("abstain", blocked[0]["status"], conflicting_ids=blocked[0].get("conflicting_ids", []),
                          observed_ids=blocked[0].get("observed_ids", []))
        return result("abstain", "unsupported_combination")
