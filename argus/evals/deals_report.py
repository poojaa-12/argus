from __future__ import annotations

import json
from pathlib import Path

from argus.evals.deals import evaluate_deals
from argus.evals.report import write_json_atomic


def main() -> None:
    payload = evaluate_deals()
    out_path = Path("eval_report_deals.json")
    write_json_atomic(out_path, payload)
    print(json.dumps({k: payload[k] for k in payload if k != "deals"}, indent=2))
    print(f"\nWrote {out_path.resolve()}")


if __name__ == "__main__":
    main()
