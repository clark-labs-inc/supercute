"""Deterministic self-check: every generator's own ground-truth answer must grade
as correct. This is a consistency gate between scenarios.py and grade.py -- it runs
NO model and costs nothing. A task that fails here would record phantom "failures"
during harvesting, poisoning the benchmark, so this must be 100% clean before any run.

We also exercise a couple of near-miss response shapes (markdown bold, a trailing
explanation line) so a reasoning model's verbosity does not get mis-graded.
"""
from __future__ import annotations

import collections

from supercute.grade import grade
from supercute.run import make_scenarios
from supercute.scenarios import TASKS


def _decorations(scn):
    """Plausible answer-bearing responses a model might emit for this scenario."""
    a = scn["answer"]
    forms = [a, f"{a}\n", f" {a} ", f"Answer: {a}"]
    if scn["kind"] == "int":
        forms += [f"The answer is {a}.", f"**{a}**"]
    elif scn["kind"] == "yn":
        forms += [a.capitalize(), f"{a.capitalize()}, that is correct."]
    else:  # str
        forms += [f'"{a}"', f"`{a}`"]
    return forms


def main(per_task=60, seed=777):
    scns = make_scenarios(sorted(TASKS), per_task, seed)
    bad = collections.defaultdict(list)
    for scn in scns:
        for form in _decorations(scn):
            if not grade(scn, form):
                bad[scn["task"]].append((scn["id"], repr(form), scn["answer"]))

    by_task = collections.Counter(s["task"] for s in scns)
    print(f"self-check: {len(scns)} scenarios x ~{len(_decorations(scns[0]))} response forms\n")
    if not bad:
        print(f"ALL {len(by_task)} TASKS CLEAN")
        return 0
    print(f"FAILURES in {len(bad)} task(s):")
    for t, rows in sorted(bad.items()):
        print(f"\n  {t}  ({len(rows)} mis-grades, {by_task[t]} scenarios)")
        for sid, form, ans in rows[:4]:
            print(f"    {sid}: graded WRONG  resp={form}  truth={ans!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
