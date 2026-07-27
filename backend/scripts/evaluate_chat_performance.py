"""Record chat streaming latency for a fixed evaluation set.

This is preparation for the second-stage routing/prompt evaluation. It does not
change application behavior and only sends requests when explicitly invoked.
"""

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import httpx


MERMAID_FENCE = re.compile(
    r"```mermaid\s*([\s\S]*?)```",
    flags=re.IGNORECASE,
)


def validate_mermaid_sources(answer):
    sources = [source.strip() for source in MERMAID_FENCE.findall(answer)]
    suspicious = sum(
        bool(re.search(r"[\uac00-\ud7af\ufffd]", source))
        for source in sources
    )
    if not sources:
        return {
            "count": 0,
            "valid": 0,
            "invalid": 0,
            "suspicious_text": 0,
            "validator_available": True,
        }
    validator = (
        Path(__file__).parents[2]
        / "frontend"
        / "scripts"
        / "validate-mermaid.mjs"
    )
    valid = 0
    validator_available = True
    for source in sources:
        try:
            result = subprocess.run(
                ["node", str(validator)],
                input=source,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=20,
                check=False,
            )
            valid += int(result.returncode == 0)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            validator_available = False
            break
    return {
        "count": len(sources),
        "valid": valid if validator_available else None,
        "invalid": len(sources) - valid if validator_available else None,
        "suspicious_text": suspicious,
        "validator_available": validator_available,
    }


def iter_sse_lines(response):
    event_type = None
    data_lines = []
    for line in response.iter_lines():
        if not line:
            if event_type and data_lines:
                yield event_type, json.loads("\n".join(data_lines))
            event_type = None
            data_lines = []
        elif line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())


def run_case(client, base_url, token, case, class_id):
    started_at = time.perf_counter()
    first_content_at = None
    visual_supplement_at = None
    content = []
    statuses = []
    with client.stream(
        "POST",
        f"{base_url.rstrip('/')}/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": case["question"],
            "class_id": class_id,
        },
    ) as response:
        response.raise_for_status()
        for event_type, payload in iter_sse_lines(response):
            if event_type == "status":
                stage = payload.get("stage")
                statuses.append(stage)
                if stage == "generating_visual" and visual_supplement_at is None:
                    visual_supplement_at = time.perf_counter()
            elif event_type == "content":
                if first_content_at is None:
                    first_content_at = time.perf_counter()
                content.append(payload.get("delta", ""))
            elif event_type == "error":
                content.append(payload.get("message", ""))
    completed_at = time.perf_counter()
    answer = "".join(content)
    has_mermaid = "```mermaid" in answer.lower()
    visual_expected = bool(case.get("expects_mermaid", False))
    mermaid_validation = validate_mermaid_sources(answer)
    return {
        "id": case["id"],
        "intent": case.get("intent"),
        "first_content_ms": (
            round((first_content_at - started_at) * 1000, 2)
            if first_content_at else None
        ),
        "total_ms": round((completed_at - started_at) * 1000, 2),
        "visual_supplement_ms": (
            round((completed_at - visual_supplement_at) * 1000, 2)
            if visual_supplement_at else None
        ),
        "content_length": len(answer),
        "statuses": statuses,
        "visual_expected": visual_expected,
        "has_mermaid": has_mermaid,
        "visual_compliant": not visual_expected or has_mermaid,
        "visual_supplement_used": "generating_visual" in statuses,
        "mermaid_validation": mermaid_validation,
        "has_source_section": "**来源**" in answer,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--class-id", type=int)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).parents[1] / "tests/fixtures/chat_intent_cases.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    results = []
    with httpx.Client(timeout=120.0) as client:
        for case in cases:
            if case.get("requires_image"):
                continue
            results.append(
                run_case(client, args.base_url, args.token, case, args.class_id)
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    visual_cases = [row for row in results if row["visual_expected"]]
    diagrams = sum(row["mermaid_validation"]["count"] for row in results)
    validator_available = all(
        row["mermaid_validation"]["validator_available"]
        for row in results
    )
    valid_diagrams = (
        sum(row["mermaid_validation"]["valid"] for row in results)
        if validator_available else None
    )
    suspicious_diagrams = sum(
        row["mermaid_validation"]["suspicious_text"]
        for row in results
    )
    payload = {
        "summary": {
            "case_count": len(results),
            "visual_expected_count": len(visual_cases),
            "visual_compliant_count": sum(
                row["visual_compliant"] for row in visual_cases
            ),
            "visual_compliance_rate": (
                round(
                    sum(row["visual_compliant"] for row in visual_cases)
                    / len(visual_cases),
                    4,
                )
                if visual_cases else None
            ),
            "visual_supplement_count": sum(
                row["visual_supplement_used"] for row in results
            ),
            "visual_supplement_rate": (
                round(
                    sum(row["visual_supplement_used"] for row in visual_cases)
                    / len(visual_cases),
                    4,
                )
                if visual_cases else None
            ),
            "average_visual_supplement_ms": (
                round(
                    sum(
                        row["visual_supplement_ms"]
                        for row in results
                        if row["visual_supplement_ms"] is not None
                    )
                    / sum(
                        row["visual_supplement_ms"] is not None
                        for row in results
                    ),
                    2,
                )
                if any(
                    row["visual_supplement_ms"] is not None
                    for row in results
                ) else None
            ),
            "mermaid_count": diagrams,
            "mermaid_valid_count": valid_diagrams,
            "mermaid_validator_available": validator_available,
            "mermaid_suspicious_text_count": suspicious_diagrams,
            "mermaid_parse_rate": (
                round(valid_diagrams / diagrams, 4)
                if diagrams and validator_available else None
            ),
        },
        "results": results,
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
