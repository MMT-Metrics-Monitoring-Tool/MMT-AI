"""Runs the evaluation questions against the configured model and prompt.

Usage (from the backend directory):
    python -m evals.run                     # all cases once
    python -m evals.run --repeat 3          # each case three times, to see how stable answers are
    python -m evals.run --case next_deadline --verbose
    python -m evals.run --min-pass 0.9      # exit code 1 below a 90 % pass rate (for CI)

Course pages are fetched live, while today's date and the project data are fixed per case (see cases.json),
so results stay comparable between runs. Results are also written to evals/results/.
"""
from datetime import date, datetime
from dotenv import load_dotenv
from pathlib import Path

from chatbot.context import ContextBuilder
from chatbot.course_content import CourseContent
from chatbot.llm import StreamResult, build_llm_client
from chatbot.prompt_loader import PromptLoader

import argparse
import json
import re
import sys


EVALS_DIR = Path(__file__).parent


def check_answer(answer: str, case: dict) -> list[str]:
    """Returns the failed checks of an answer. Patterns are case-insensitive regular expressions."""
    failures = []
    for pattern in case.get("must_match", []):
        if not re.search(pattern, answer, re.IGNORECASE | re.MULTILINE):
            failures.append(f"missing /{pattern}/")
    for pattern in case.get("must_not_match", []):
        if re.search(pattern, answer, re.IGNORECASE | re.MULTILINE):
            failures.append(f"unexpected /{pattern}/")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--case", action="append", help="Run only the given case ID (repeatable).")
    parser.add_argument("--min-pass", type=float, default=0.0, help="Minimum pass rate (0-1) for exit code 0.")
    parser.add_argument("--verbose", action="store_true", help="Print every answer.")
    args = parser.parse_args()

    load_dotenv()
    spec = json.loads((EVALS_DIR / "cases.json").read_text(encoding="utf-8"))
    defaults = spec["defaults"]
    cases = [case for case in spec["cases"] if not args.case or case["id"] in args.case]

    llm = build_llm_client()
    context = ContextBuilder(
        prompt_loader=PromptLoader(),
        course_content=CourseContent(),
        get_project_snapshot=lambda project_id: "",
    )
    print(f"Model {llm.model}, prompt version {context.prompt_version}, {len(cases)} cases x {args.repeat}\n")

    results = []
    for case in cases:
        project = case.get("project", defaults["project"])
        today = date.fromisoformat(case.get("today", defaults["today"]))
        # The fixtures contain the project's current_date; keep it in line with the case's date.
        snapshot = re.sub(
            r"current_date: \d{4}-\d{2}-\d{2}", f"current_date: {today.isoformat()}",
            (EVALS_DIR / "fixtures" / f"{project}.txt").read_text(encoding="utf-8"),
        )
        messages = context.build_messages(
            case["question"], case.get("history", []), project_id=0, today=today, project_snapshot=snapshot,
        )
        for run in range(args.repeat):
            stream = StreamResult()
            try:
                for _ in llm.stream(messages, stream):
                    pass
                failures = check_answer(stream.text, case)
                if stream.finish_reason == "length":
                    failures.append("truncated: hit LLM_MAX_TOKENS (hidden thinking counts towards it)")
            except Exception as exc:
                failures = [f"error: {type(exc).__name__}: {exc}"]
            passed = not failures
            results.append({
                "id": case["id"], "run": run, "passed": passed, "failures": failures, "answer": stream.text,
                "first_token_ms": stream.first_token_ms, "total_ms": stream.total_ms,
                "prompt_tokens": stream.prompt_tokens, "completion_tokens": stream.completion_tokens,
                "finish_reason": stream.finish_reason,
            })
            timing = f"{(stream.first_token_ms or 0) / 1000:5.1f}s first, {(stream.total_ms or 0) / 1000:5.1f}s total"
            print(f"{'PASS' if passed else 'FAIL'}  {case['id']:<34} {timing}  {'; '.join(failures)}")
            if args.verbose or not passed:
                print("      " + stream.text.strip().replace("\n", "\n      ") + "\n")

    pass_rate = sum(r["passed"] for r in results) / len(results) if results else 0.0
    first_tokens = sorted(r["first_token_ms"] for r in results if r["first_token_ms"] is not None)
    median_first = first_tokens[len(first_tokens) // 2] / 1000 if first_tokens else float("nan")
    print(f"\nPassed {sum(r['passed'] for r in results)}/{len(results)} ({pass_rate:.0%}), "
          f"median time to first token {median_first:.1f}s")

    out_dir = EVALS_DIR / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out_file.write_text(json.dumps({
        "model": llm.model, "prompt_version": context.prompt_version, "pass_rate": pass_rate, "results": results,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Results written to {out_file.relative_to(EVALS_DIR.parent)}")

    return 0 if pass_rate >= args.min_pass else 1


if __name__ == "__main__":
    sys.exit(main())
