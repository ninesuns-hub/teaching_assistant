"""Record chat streaming latency for a fixed evaluation set.

This is preparation for the second-stage routing/prompt evaluation. It does not
change application behavior and only sends requests when explicitly invoked.
"""

import argparse
import json
import time
from pathlib import Path

import httpx


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
                statuses.append(payload.get("stage"))
            elif event_type == "content":
                if first_content_at is None:
                    first_content_at = time.perf_counter()
                content.append(payload.get("delta", ""))
            elif event_type == "error":
                content.append(payload.get("message", ""))
    completed_at = time.perf_counter()
    answer = "".join(content)
    return {
        "id": case["id"],
        "intent": case.get("intent"),
        "first_content_ms": (
            round((first_content_at - started_at) * 1000, 2)
            if first_content_at else None
        ),
        "total_ms": round((completed_at - started_at) * 1000, 2),
        "content_length": len(answer),
        "statuses": statuses,
        "has_mermaid": "```mermaid" in answer,
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
    args.output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
