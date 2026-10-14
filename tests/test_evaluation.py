from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from logic_foundry.data import case_fingerprint
from logic_foundry.evaluation import evaluate, render_evaluation


class FixtureConsumer:
    """Control consumer outcomes so these tests isolate assessment semantics."""

    def __init__(self, artifact):
        self.artifact = artifact

    def predict(self, inputs):
        return deepcopy(inputs["prediction"])


def artifact():
    return {
        "artifact_id": "frozen-artifact",
        "task": {
            "task_id": "synthetic-routing",
            "title": "Synthetic routing",
            "purpose": "reproduce_historical_judgments",
            "synthetic": True,
            "judgment_authority": "provisional",
            "target_ids": ["A", "B"],
        },
        "baseline": {"targets": ["A"], "support_count": 8},
        "scope": {"field": "scope", "equals": "routine"},
        "provenance": {
            "development_sha256": "development-digest",
            "development_record_ids": ["dev-1"],
            "development_group_ids": ["development-group"],
            "development_case_fingerprints": [],
            "task_sha256": "task-digest",
            "codebook_sha256": "codebook-digest",
        },
        "limitations": ["Only a fixture."],
    }


def record(record_id, expected, predicted, *, status="resolved", tags=None):
    return {
        "id": record_id,
        "group_id": f"group-{record_id}",
        "observed_at": "2026-01-01",
        "inputs": {
            "unique_case": record_id,
            "scope": "routine",
            "prediction": {
                "status": "abstain" if predicted is None else "decided",
                "targets": predicted,
                "reason": "fixture result",
            },
        },
        "judgment": {"status": status, "targets": expected},
        "tags": tags or [],
    }


class EvaluationTests(unittest.TestCase):
    def run_evaluation(self, frozen, rows, digest="assessment-digest"):
        with patch("logic_foundry.evaluation.Consumer", FixtureConsumer):
            return evaluate(frozen, rows, digest)

    def test_resolved_metrics_include_abstentions_and_explicit_empty_mapping(self):
        rows = [
            record("a", ["A"], ["A"], tags=["common"]),
            record("b", ["A", "B"], ["A"], tags=["rare"]),
            record("c", ["B"], None, tags=["rare"]),
            record("d", [], [], tags=["common"]),
            record("e", None, ["B"], status="unannotated", tags=["rare"]),
        ]
        report = self.run_evaluation(artifact(), rows)
        self.assertEqual(report["metrics"], {
            "resolved_total": 4, "correct": 2, "incorrect": 1, "abstained": 1,
            "decided": 3, "exact_agreement": 0.5, "coverage": 0.75,
            "covered_exact_agreement": 2 / 3,
        })
        self.assertEqual(report["baseline"]["metrics"]["exact_agreement"], 0.25)
        self.assertEqual(report["baseline"]["metrics"]["coverage"], 1.0)
        self.assertEqual(report["baseline"]["targets"], ["A"])
        self.assertTrue(all(row["baseline"]["targets"] == ["A"] for row in report["rows"]))
        self.assertEqual([row["id"] for row in report["discrepancies"]], ["b"])
        self.assertEqual([row["id"] for row in report["abstentions"]], ["c"])
        self.assertEqual(report["per_target"]["B"]["fn"], 1)
        self.assertEqual(report["per_target"]["B"]["abstained_reference_positive"], 1)
        self.assertEqual(report["per_target"]["B"]["fp"], 0)
        rare = report["groups"]["tags"]["rare"]
        self.assertEqual(rare["n"], 2)
        self.assertEqual(rare["unresolved_count"], 1)
        self.assertEqual(rare["coverage"], 0.5)
        self.assertEqual(rare["agreement"], 0.0)
        self.assertEqual(report["groups"]["empty_target_set"]["explicit empty judgment"]["agreement"], 1.0)

    def test_disputed_allowed_sets_are_diagnostics_and_not_correctness(self):
        disputed = record("disputed", None, ["B", "A"], status="disputed", tags=["uncertain"])
        disputed["judgment"]["acceptable_targets"] = [["A"], ["A", "B"]]
        report = self.run_evaluation(artifact(), [disputed, record("missing", None, None, status="unannotated")])
        self.assertEqual(report["metrics"]["resolved_total"], 0)
        self.assertIsNone(report["metrics"]["exact_agreement"])
        self.assertIsNone(report["metrics"]["coverage"])
        self.assertIsNone(report["baseline"]["metrics"]["exact_agreement"])
        self.assertEqual(report["unresolved_references"]["counts"], {"disputed": 1, "unannotated": 1})
        self.assertEqual(len(report["unresolved_references"]["rows"]), 2)
        self.assertTrue(report["disputed_diagnostics"][0]["decision_matches_allowed_set"])
        self.assertTrue(all(row["comparison"] == "unresolved_reference" for row in report["rows"]))
        self.assertEqual(report["per_target"]["A"]["tp"], 0)
        self.assertEqual(report["per_target"]["B"]["fn"], 0)
        self.assertEqual(report["groups"]["tags"]["uncertain"]["n"], 0)
        self.assertEqual([row["id"] for row in report["abstentions"]], ["missing"])

    def test_multitarget_agreement_uses_sets_and_counts_false_positives(self):
        report = self.run_evaluation(artifact(), [
            record("ordered", ["A", "B"], ["B", "A"]),
            record("extra", [], ["B"]),
        ])
        self.assertEqual(report["metrics"]["correct"], 1)
        self.assertEqual(report["metrics"]["incorrect"], 1)
        self.assertEqual(report["per_target"]["B"]["tp"], 1)
        self.assertEqual(report["per_target"]["B"]["fp"], 1)
        self.assertEqual(report["per_target"]["B"]["precision"], 0.5)

    def test_all_abstentions_have_undefined_covered_agreement(self):
        report = self.run_evaluation(artifact(), [record("a", ["A"], None)])
        self.assertEqual(report["metrics"]["exact_agreement"], 0.0)
        self.assertEqual(report["metrics"]["coverage"], 0.0)
        self.assertIsNone(report["metrics"]["covered_exact_agreement"])

    def test_untagged_scope_groups_include_null_and_missing_and_preserve_json_types(self):
        frozen = artifact()
        frozen["scope"]["equals"] = False
        rows = [
            record("in", ["A"], ["A"]),
            record("numeric", ["B"], ["A"]),
            record("outside", ["A"], None),
            record("null", ["B"], None),
            record("missing", ["A"], None),
        ]
        for row, value in zip(rows, [False, 0, True, None]):
            row["inputs"]["scope"] = value
        del rows[-1]["inputs"]["scope"]
        report = self.run_evaluation(frozen, rows)
        groups = report["groups"]["scope"]
        self.assertEqual(groups["in_scope"]["n"], 1)
        self.assertEqual(groups["in_scope"]["agreement"], 1.0)
        self.assertEqual(groups["outside_scope"]["n"], 2)
        self.assertEqual(groups["outside_scope"]["coverage"], 0.5)
        self.assertEqual(groups["missing_scope"]["n"], 2)
        self.assertEqual(groups["missing_scope"]["coverage"], 0.0)
        self.assertEqual(report["metrics"]["resolved_total"], 5)
        self.assertEqual(report["metrics"]["exact_agreement"], 0.2)
        self.assertEqual(report["metrics"]["coverage"], 0.4)
        self.assertEqual(report["baseline"]["metrics"]["coverage"], 1.0)
        self.assertEqual(report["groups"]["tags"], {})
        rendered = render_evaluation(report)
        self.assertIn("In-scope resolved references: 1", rendered)
        self.assertIn("including outside-scope and missing-scope cases", rendered)
        self.assertIn("scope: missing_scope", rendered)

    def test_refuses_each_leakage_channel_before_calling_consumer(self):
        source = record("assessment", ["A"], ["A"])
        scenarios = [
            ("digest", "development-digest", None, None),
            ("record IDs", "assessment-digest", "development_record_ids", [source["id"]]),
            ("case groups", "assessment-digest", "development_group_ids", [source["group_id"]]),
            ("case fingerprints", "assessment-digest", "development_case_fingerprints", [case_fingerprint(source)]),
        ]
        for expected, digest, key, value in scenarios:
            with self.subTest(channel=expected):
                frozen = artifact()
                if key:
                    frozen["provenance"][key] = value
                with patch("logic_foundry.evaluation.Consumer") as consumer:
                    with self.assertRaises(ValueError):
                        evaluate(frozen, [source], digest)
                    consumer.assert_not_called()

    def test_fingerprint_leak_rejects_renamed_case_with_changed_reference(self):
        development = record("original", ["A"], ["A"])
        assessment = deepcopy(development)
        assessment["id"] = "renamed"
        assessment["group_id"] = "new-group"
        assessment["judgment"] = {"status": "unannotated", "targets": None}
        frozen = artifact()
        frozen["provenance"]["development_case_fingerprints"] = [case_fingerprint(development)]
        with self.assertRaisesRegex(ValueError, "fingerprints"):
            self.run_evaluation(frozen, [assessment])

    def test_empty_and_duplicate_assessment_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            self.run_evaluation(artifact(), [])
        duplicate = record("same-id", ["A"], ["A"])
        with self.assertRaisesRegex(ValueError, "unique"):
            self.run_evaluation(artifact(), [duplicate, deepcopy(duplicate)])

    def test_assessment_is_deterministic_and_does_not_mutate_artifact_or_rows(self):
        frozen = artifact()
        rows = [record("z", ["B"], ["A"]), record("a", ["A"], ["A"])]
        original_artifact, original_rows = deepcopy(frozen), deepcopy(rows)
        report = self.run_evaluation(frozen, rows)
        reordered_report = self.run_evaluation(frozen, list(reversed(rows)))
        self.assertEqual(json.dumps(report, sort_keys=True), json.dumps(reordered_report, sort_keys=True))
        self.assertEqual(frozen, original_artifact)
        self.assertEqual(rows, original_rows)
        self.assertTrue(any("real-data validation is pending" in value for value in report["limitations"]))
        rendered = render_evaluation(report)
        self.assertIn("discrepancy", rendered)
        self.assertIn("Development majority", rendered)
        self.assertIn("real-data validation is pending", rendered)


if __name__ == "__main__":
    unittest.main()
