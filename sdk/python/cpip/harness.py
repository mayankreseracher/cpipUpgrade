"""Minimal Python harness contract for cpip.

- Define a Harness base class with a run(params) method.
- Provide a serve(harness) helper that reads JSON params from stdin and writes JSON to stdout.

This is intentionally lightweight for examples.
"""
from __future__ import annotations
import sys
import json
from typing import Any, Dict

class Harness:
    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()


def serve(h: Harness) -> None:
    # simple loop: read lines from stdin; each line is a JSON params object; run and print JSON result
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            params = json.loads(line)
        except Exception:
            params = {}
        try:
            result = h.run(params)
        except Exception as e:
            result = {"error": str(e)}
        sys.stdout.write(json.dumps(result) + "\n")
        sys.stdout.flush()
