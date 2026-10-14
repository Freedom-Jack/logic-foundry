from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from logic_foundry.consumer import Consumer, seal_artifact
from logic_foundry.data import (file_sha256, load_records, load_reference, load_task,
                                profile, validate_records, validate_reference)
from logic_foundry.discovery import discover
from logic_foundry.evaluation import evaluate


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "examples" / "synthetic"


def build(task=None, records=None, reference=True):
    path = FIXTURES / "task.json"
    task = deepcopy(task) if task is not None else load_task(path)
    records = deepcopy(records) if records is not None else load_records(FIXTURES / "development.jsonl", task)
    codebook, sha = load_reference(task, path) if reference else (None, None)
    return discover(task, records, file_sha256(FIXTURES / "development.jsonl"), file_sha256(path), codebook, sha)


class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact, cls.evidence = build()
        cls.consumer = Consumer(cls.artifact)
        cls.task = load_task(FIXTURES / "task.json")

    def test_complete_path_records_investigation_and_traceable_claims(self):
        self.assertTrue(self.artifact["rules"])
        self.assertTrue(self.artifact["reference"])
        investigation = self.evidence["investigation"]
        self.assertEqual(investigation["action"], "resolve_reference")
        self.assertEqual(investigation["effect"], "changed")
        self.assertTrue(investigation["evidence"]["unresolved_record_ids"])
        all_ids = set(self.artifact["provenance"]["development_record_ids"])
        for candidate in self.evidence["candidate_comparison"]:
            for claim in candidate["claims"]:
                self.assertTrue(set(claim["observed_ids"]) <= all_ids)
                self.assertTrue(set(claim["supporting_ids"]).isdisjoint(claim["conflicting_ids"]))
        self.assertTrue(any(c["conflicting_ids"] for candidate in self.evidence["candidate_comparison"] for c in candidate["claims"]))

    def test_new_alias_uses_bundled_reference_without_unused_inputs(self):
        self.assertNotIn("channel", self.artifact["input_requirements"])
        result = self.consumer.predict({"intake_code": "H52", "expedited": True, "scope": "routine"})
        self.assertEqual(result["targets"], ["billing", "escalation"])
        self.assertEqual(result["status"], "decided")
        self.assertTrue(result["evidence_ids"])

    def test_explicit_empty_is_a_decision_and_multiple_targets_are_preserved(self):
        empty = self.consumer.predict({"intake_code": "D61", "expedited": False, "scope": "routine"})
        self.assertEqual((empty["status"], empty["targets"]), ("decided", []))
        combined = self.consumer.predict({"intake_code": "E83", "expedited": True, "scope": "routine"})
        self.assertEqual(combined["targets"], ["billing", "escalation", "privacy"])

    def test_information_gaps_conflicts_and_outside_scope_abstain(self):
        defaults = {"intake_code": "H52", "expedited": False, "scope": "routine"}
        scenarios = [
            ({**defaults, "intake_code": "missing-code"}, "unresolved_reference"),
            ({**defaults, "intake_code": "P73"}, "conflicted_evidence"),
            ({**defaults, "intake_code": "A52"}, "conflicted_evidence"),
            ({**defaults, "intake_code": "D61", "expedited": True}, "insufficient_support"),
            ({**defaults, "expedited": None}, "missing_input"),
            ({**defaults, "expedited": 0}, "invalid_input_type"),
            ({**defaults, "scope": "exceptional"}, "outside_scope"),
        ]
        for inputs, reason in scenarios:
            with self.subTest(reason=reason):
                result = self.consumer.predict(inputs)
                self.assertEqual(result["status"], "abstain")
                self.assertIsNone(result["targets"])
                self.assertEqual(result["reason"], reason)

    def test_artifact_and_reference_integrity_and_versions(self):
        broken = deepcopy(self.artifact)
        broken["rules"][0]["targets"] = ["changed-target"]
        with self.assertRaisesRegex(ValueError, "integrity"):
            Consumer(broken)
        broken = deepcopy(self.artifact)
        broken["reference"]["entries"]["H52"]["topic"] = "shipment"
        with self.assertRaisesRegex(ValueError, "reference integrity"):
            Consumer(seal_artifact(broken))
        reference, _ = load_reference(self.task, FIXTURES / "task.json")
        reference["version"] = "different-version"
        with self.assertRaisesRegex(ValueError, "version"):
            validate_reference(reference, self.task)

    def test_conflicting_imported_rules_abstain_without_arbitrary_ordering(self):
        artifact = deepcopy(self.artifact)
        duplicate = deepcopy(next(r for r in artifact["rules"] if r["conditions"] == {"expedited": True, "topic": "payments"}))
        duplicate.update(rule_id="contradictory-extra-rule", targets=["privacy"])
        artifact["rules"].append(duplicate)
        result = Consumer(seal_artifact(artifact)).predict({"intake_code": "H52", "expedited": True, "scope": "routine"})
        self.assertEqual(result["reason"], "conflicting_rules")
        self.assertEqual(len(result["matched_rule_ids"]), 2)

    def test_unannotated_and_disputed_records_do_not_create_training_support(self):
        records = load_records(FIXTURES / "development.jsonl", self.task)
        resolved_only = [r for r in records if r["judgment"]["status"] == "resolved"]
        artifact, _ = build(records=resolved_only)
        self.assertEqual(artifact["rules"], self.artifact["rules"])
        self.assertEqual(artifact["baseline"], self.artifact["baseline"])
        unresolved = [r for r in records if r["judgment"]["status"] != "resolved"]
        self.assertTrue(unresolved)
        support_ids = {i for r in self.artifact["rules"] for i in r["supporting_ids"]}
        self.assertFalse(support_ids & {r["id"] for r in unresolved})

    def test_repeated_group_cannot_supply_independent_support(self):
        records = load_records(FIXTURES / "development.jsonl", self.task)[:4]
        for row in records:
            row["group_id"] = "one-related-family"
        # Preserve a second group for grouped comparison, but its cell differs.
        other = deepcopy(records[0])
        other.update(id="other", group_id="independent-family")
        other["inputs"]["expedited"] = True
        other["judgment"]["targets"] = ["billing", "escalation"]
        artifact, _ = build(records=records + [other])
        self.assertEqual(artifact["rules"], [])
        self.assertTrue(all(c["status"] != "supported" for c in artifact["blocked_cells"]))
        self.assertTrue(all(c["support_group_count"] <= 1 for c in artifact["blocked_cells"]))

    def test_singletons_do_not_confirm_a_rule_in_fallback_investigation(self):
        task = deepcopy(self.task)
        task.pop("reference")
        task["input_fields"] = {"intake_code": task["input_fields"]["intake_code"], "scope": task["input_fields"]["scope"]}
        records = load_records(FIXTURES / "development.jsonl", self.task)[:2]
        for number, record in enumerate(records):
            record["inputs"] = {"intake_code": "distinct-" + str(number), "scope": "routine"}
        artifact, evidence = build(task=task, records=records, reference=False)
        self.assertEqual(artifact["rules"], [])
        self.assertEqual(evidence["investigation"]["effect"], "limited")
        self.assertIn("No supported", evidence["investigation"]["conclusion"])

    def test_no_complete_feature_values_exports_an_explicit_abstaining_artifact(self):
        task = deepcopy(self.task)
        task.pop("reference")
        task["input_fields"] = {"intake_code": task["input_fields"]["intake_code"], "scope": task["input_fields"]["scope"]}
        records = load_records(FIXTURES / "development.jsonl", self.task)[:2]
        for record in records:
            record["inputs"] = {"scope": "routine"}
        artifact, evidence = build(task=task, records=records, reference=False)
        self.assertEqual(artifact["rules"], [])
        self.assertEqual(evidence["investigation"]["effect"], "limited")
        self.assertEqual(Consumer(artifact).predict({"intake_code": "new", "scope": "routine"})["status"], "abstain")

    def test_validation_rejects_ambiguous_labels_and_duplicate_ids(self):
        records = load_records(FIXTURES / "development.jsonl", self.task)[:2]
        bad = deepcopy(records)
        bad[0]["judgment"] = {"status": "unannotated", "targets": []}
        with self.assertRaisesRegex(ValueError, "null"):
            validate_records(bad, self.task)
        with self.assertRaisesRegex(ValueError, "Duplicate record"):
            validate_records([records[0], deepcopy(records[0])], self.task)
        bad = deepcopy(records)
        bad[0]["judgment"]["targets"] = ["undeclared"]
        with self.assertRaisesRegex(ValueError, "declared target"):
            validate_records(bad, self.task)

    def test_profile_uses_chronological_time_not_lexical_offset_order(self):
        records = load_records(FIXTURES / "development.jsonl", self.task)[:2]
        records[0]["observed_at"] = "2026-01-02T01:00:00+03:00"
        records[1]["observed_at"] = "2026-01-01T23:00:00+00:00"
        bounds = profile(records, self.task)["observed_at_range"]
        self.assertEqual(bounds, ["2026-01-01T22:00:00+00:00", "2026-01-01T23:00:00+00:00"])

    def test_reference_investigation_does_not_invent_observed_shared_aliases(self):
        records = load_records(FIXTURES / "development.jsonl", self.task)
        _, evidence = build(records=records[:2] + records[8:10])
        self.assertEqual(evidence["investigation"]["action"], "resolve_reference")
        self.assertIn("no shared meaning", evidence["investigation"]["conclusion"])

    def test_declared_post_decision_fields_are_excluded_from_discovery(self):
        task = deepcopy(self.task)
        task["input_fields"]["previous_route"] = {"type": "categorical", "available_at_decision": False}
        records = load_records(FIXTURES / "development.jsonl", self.task)
        for record in records:
            record["inputs"]["previous_route"] = json.dumps(record["judgment"]["targets"])
        artifact, evidence = build(task=task, records=records)
        self.assertEqual(artifact["rules"], self.artifact["rules"])
        self.assertNotIn("previous_route", artifact["input_requirements"])
        self.assertTrue(all("previous_route" not in c["features"] for c in evidence["candidate_comparison"]))

    def test_frozen_consumer_evaluation_does_not_change_with_reference_labels(self):
        records = load_records(FIXTURES / "assessment.jsonl", self.task)
        before = deepcopy(self.artifact)
        first = evaluate(self.artifact, records, file_sha256(FIXTURES / "assessment.jsonl"))
        records[0]["judgment"]["targets"] = ["privacy"]
        second = evaluate(self.artifact, records, "changed-assessment-digest")
        self.assertEqual(self.artifact, before)
        self.assertEqual(first["rows"][0]["decision"], second["rows"][0]["decision"])
        self.assertEqual(second["metrics"]["incorrect"], first["metrics"]["incorrect"] + 1)

    def test_cli_demo_is_byte_reproducible_and_export_runs_outside_project(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo"
            command = [sys.executable, "-B", "-m", "logic_foundry", "demo", "--out", str(output)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            files = {p.name: p.read_bytes() for p in output.iterdir()}
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(files, {p.name: p.read_bytes() for p in output.iterdir()})
            # Fresh process from another directory: only the package and artifact are accessed.
            script = "\n".join([
                "import json, sys",
                "sys.path.insert(0, sys.argv[1])",
                "from logic_foundry.consumer import Consumer",
                "print(json.dumps(Consumer.from_path(sys.argv[2]).predict({'intake_code':'H52','expedited':True,'scope':'routine'})))",
            ])
            prediction = subprocess.run([sys.executable, "-B", "-c", script, str(ROOT), str(output / "artifact.json")],
                                        cwd=directory, capture_output=True, text=True)
            self.assertEqual(prediction.returncode, 0, prediction.stderr)
            self.assertEqual(json.loads(prediction.stdout)["targets"], ["billing", "escalation"])
            rejection = subprocess.run([sys.executable, "-B", "-m", "logic_foundry", "evaluate", "--artifact", str(output / "artifact.json"),
                                        "--cases", str(FIXTURES / "development.jsonl"), "--out", str(output / "invalid")],
                                       cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(rejection.returncode, 2)
            self.assertIn("development collection", rejection.stderr)
            self.assertFalse((output / "invalid").exists())


if __name__ == "__main__":
    unittest.main()
