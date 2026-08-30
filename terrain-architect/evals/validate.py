import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_AXES = {
    "attribution",
    "diagnosis",
    "design",
    "implementation",
    "trap-resistance",
}


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


# Every capability eval must carry exactly this shape. Named here rather than
# implied by the checks below, so a malformed entry is reported as a schema
# violation and not as a KeyError from whichever check happened to touch it
# first.
REQUIRED_KEYS = {"id", "axis", "prompt", "expected_output", "expectations"}


def validate_capability_evals():
    payload = load_json(ROOT / "evals.json")
    assert payload["skill_name"] == "terrain-architect"
    evals = payload["evals"]
    ids = [item["id"] for item in evals]
    assert len(ids) == len(set(ids)), "Capability eval IDs must be unique"

    # ⚠️ THE SHAPE IS CHECKED FIRST, AND IT DID NOT USED TO BE. Two evals were
    # once appended with `assertions` instead of `expectations` and no `axis`
    # at all. The axis check below then died with a bare `KeyError: 'axis'`
    # inside a set comprehension -- a traceback that names the line but not the
    # entry, so the failure read as a bug in the validator rather than as two
    # malformed records. It took the whole eval suite red until someone looked.
    malformed = [
        "eval %r is missing %s" % (item.get("id", "<no id>"),
                                   ", ".join(sorted(REQUIRED_KEYS - set(item))))
        for item in evals if not REQUIRED_KEYS <= set(item)
    ]
    assert not malformed, "\n".join(malformed)

    missing_axes = REQUIRED_AXES - {item["axis"] for item in evals}
    assert not missing_axes, (
        "no eval covers these required axes: %s" % ", ".join(sorted(missing_axes)))
    for item in evals:
        assert item["prompt"].strip(), "eval %r has an empty prompt" % item["id"]
        assert item["expected_output"].strip(), (
            "eval %r has an empty expected_output" % item["id"])
        assert len(item["expectations"]) >= 2, (
            "eval %r needs at least two expectations" % item["id"])
        assert all(e.strip() for e in item["expectations"]), (
            "eval %r has a blank expectation" % item["id"])
    return {item["id"]: item for item in evals}


def validate_trigger_evals():
    evals = load_json(ROOT / "trigger-evals.json")
    assert len(evals) >= 33
    assert all(set(item) == {"query", "should_trigger"} for item in evals)
    queries = [item["query"] for item in evals]
    assert len(queries) == len(set(queries)), "Trigger queries must be unique"
    positives = [item for item in evals if item["should_trigger"] is True]
    negatives = [item for item in evals if item["should_trigger"] is False]
    assert len(positives) >= 17
    assert len(negatives) >= 16
    positive_text = " ".join(item["query"].lower() for item in positives)
    for required_scope in (
        "grand canyon",
        "node engine",
        "splatmaps",
        "lava",
        "planet",
        "cannot ship",
    ):
        assert required_scope in positive_text


def validate_historical_result(eval_by_id):
    result = load_json(ROOT / "results" / "iteration-1.json")
    assert result["status"] == "historical-non-reproducible"
    provenance = result["provenance"]
    assert provenance["reproducible_from_repository"] is False
    assert provenance["transcripts_retained"] is False
    assert provenance["grader_outputs_retained"] is False
    rows = result["results"]
    assert result["scope"] == [row["eval_id"] for row in rows]
    for row in rows:
        eval_item = eval_by_id[row["eval_id"]]
        expected_total = len(eval_item["expectations"])
        assert row["with_skill_total"] == expected_total
        assert row["baseline_total"] == expected_total
        assert 0 <= row["with_skill_passed"] <= expected_total
        assert 0 <= row["baseline_passed"] <= expected_total
    summary = result["summary"]
    assert summary["with_skill_passed"] == sum(row["with_skill_passed"] for row in rows)
    assert summary["with_skill_total"] == sum(row["with_skill_total"] for row in rows)
    assert summary["baseline_passed"] == sum(row["baseline_passed"] for row in rows)
    assert summary["baseline_total"] == sum(row["baseline_total"] for row in rows)


def validate_grounding_manifest():
    path = ROOT.parent / "references" / "open-source-grounding.json"
    payload = load_json(path)
    assert payload["schema_version"] == 1
    entries = payload["entries"]
    ids = [entry["id"] for entry in entries]
    assert len(entries) >= 9
    assert len(ids) == len(set(ids)), "Grounding entry IDs must be unique"
    for entry in entries:
        assert re.fullmatch(r"[0-9a-f]{40}", entry["revision"])
        assert entry["license"]["spdx"] in {"CC0-1.0", "GPL-3.0-only", "MIT"}
        assert entry["license"]["path"].strip()
        assert entry["source_locations"]
        assert entry["adopted_behavior"]
        assert entry["known_deviations"]
        assert entry["engine_translation"].strip()


def main():
    eval_by_id = validate_capability_evals()
    validate_trigger_evals()
    validate_historical_result(eval_by_id)
    validate_grounding_manifest()
    print("terrain-architect eval integrity: OK")


if __name__ == "__main__":
    main()
