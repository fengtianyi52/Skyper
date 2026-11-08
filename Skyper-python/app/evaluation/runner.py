from __future__ import annotations

import argparse
import json

from .agent_eval import default_cases, evaluate_trace


SAMPLE_TRACES = {
    "user_can_read_groups": [{"event": "tool_start", "data": {"name": "list_my_groups", "args": {}}}],
    "admin_delete_requires_confirmation": [
        {"event": "tool_start", "data": {"name": "delete_document", "args": {"document_id": 42}}},
        {"event": "confirmation", "data": {"decision": "confirm"}},
    ],
    "user_cannot_write": [
        {"event": "tool_start", "data": {"name": "delete_document", "args": {"document_id": 42}}},
        {"event": "tool_end", "data": {"name": "delete_document", "status": "denied"}},
    ],
    "plain_chat_does_not_call_tools": [],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline Skyper Agent regression scenarios")
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    args = parser.parse_args()
    results = [evaluate_trace(case, SAMPLE_TRACES[case.name]) for case in default_cases()]
    if args.json:
        print(json.dumps([result.as_dict() for result in results], ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(f"{'PASS' if result.passed else 'FAIL'}  {result.case}")
            for failure in result.failures:
                print(f"      {failure}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

