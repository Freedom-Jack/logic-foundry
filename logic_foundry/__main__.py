"""Run with python3 -m logic_foundry --help. No services or third-party packages."""

import argparse
import json
import sys
from pathlib import Path

from .consumer import Consumer
from .data import file_sha256, load_records, load_reference, load_task, profile, read_json, write_json
from .discovery import discover
from .reporting import render_application, render_discovery


def fit(task_path, source_path, out):
    task = load_task(task_path)
    records = load_records(source_path, task)
    reference, reference_hash = load_reference(task, task_path)
    artifact, evidence = discover(task, records, file_sha256(source_path), file_sha256(task_path), reference, reference_hash)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "artifact.json", artifact)
    write_json(out / "evidence.json", evidence)
    write_json(out / "profile.json", evidence["profile"])
    (out / "report.md").write_text(render_discovery(artifact, evidence), encoding="utf-8")
    (out / "application.md").write_text(render_application(artifact), encoding="utf-8")
    return artifact


def assess(artifact_path, cases_path, out):
    from .evaluation import evaluate, render_evaluation
    consumer = Consumer.from_path(artifact_path)
    artifact = consumer.artifact
    records = load_records(cases_path, {**artifact["task"], "input_fields": artifact["record_schema"]})
    report = evaluate(artifact, records, file_sha256(cases_path))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "evaluation.json", report)
    (out / "evaluation.md").write_text(render_evaluation(report), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract and apply bounded historical decision logic. Synthetic demo; real-data validation pending.")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="fit synthetic development data, freeze artifact, then evaluate separate cases")
    demo.add_argument("--out", type=Path, default=Path("build/demo"))
    inspect = commands.add_parser("inspect", help="profile a JSONL source without extracting or reading assessment data")
    fit_parser = commands.add_parser("fit", help="development-only inspection, investigation, selection, and export")
    for command in (inspect, fit_parser):
        command.add_argument("--task", type=Path, required=True)
        command.add_argument("--source", type=Path, required=True)
    fit_parser.add_argument("--out", type=Path, required=True)
    evaluation = commands.add_parser("evaluate", help="apply a frozen artifact to separate assessment cases; reject overlap")
    evaluation.add_argument("--artifact", type=Path, required=True)
    evaluation.add_argument("--cases", type=Path, required=True)
    evaluation.add_argument("--out", type=Path, required=True)
    predict = commands.add_parser("predict", help="apply only an exported artifact to a new input object")
    predict.add_argument("--artifact", type=Path, required=True)
    inputs = predict.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--input", help="JSON input object (quote for your shell)")
    inputs.add_argument("--case", type=Path, help="JSON file containing an input object or a record with inputs")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            task = load_task(args.task)
            print(json.dumps(profile(load_records(args.source, task), task), indent=2, sort_keys=True))
        elif args.command == "fit":
            artifact = fit(args.task, args.source, args.out)
            print("Exported {} rules using {} to {}".format(len(artifact["rules"]), artifact["selection"]["candidate_id"], args.out.resolve()))
        elif args.command == "evaluate":
            assess(args.artifact, args.cases, args.out)
            print("Assessment written to " + str(args.out.resolve() / "evaluation.md"))
        elif args.command == "predict":
            payload = json.loads(args.input) if args.input is not None else read_json(args.case)
            payload = payload.get("inputs", payload) if isinstance(payload, dict) else payload
            print(json.dumps(Consumer.from_path(args.artifact).predict(payload), indent=2, sort_keys=True))
        elif args.command == "demo":
            fixtures = Path(__file__).resolve().parent.parent / "examples" / "synthetic"
            artifact = fit(fixtures / "task.json", fixtures / "development.jsonl", args.out)
            # Persist and reload the frozen export. Only now is assessment opened.
            assess(args.out / "artifact.json", fixtures / "assessment.jsonl", args.out)
            print("SYNTHETIC demonstration; real-data validation pending.")
            print("Exported {} rules using {}.".format(len(artifact["rules"]), artifact["selection"]["candidate_id"]))
            print("Artifacts, evidence, application requirements and assessment: " + str(args.out.resolve()))
        return 0
    except (ValueError, OSError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
