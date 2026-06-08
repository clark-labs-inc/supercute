"""Adapter skeletons for turning public benchmark records into SUPERCUTE PublicLift tasks.

This file intentionally contains no third-party data. It documents the reuse path:
load a public record under its license, convert it to mutable state, generate a
long operation log with a deterministic Python oracle, and emit a normal SUPERCUTE
scenario dict: {task, kind, answer, prompt, meta}.

Recommended source families:
- Finance: FinQA, TAT-QA, ConvFinQA, MultiHiertt
- Tables/spreadsheets: TabFact, WikiTableQuestions, SpreadsheetBench
- Legal: CUAD, ContractNLI, LEDGAR, Material Contracts Corpus
- Receipts/documents: CORD, SROIE, DocVQA
- Code/software: CRUXEval, LiveCodeBench, CodeNet, SWE-bench
- Logs/ops: LogHub / LogHub-2.0

The important design rule: never ask the original benchmark question directly.
That invites memorization and short-horizon shortcuts. Instead, use the public
record as realistic substrate and generate fresh, seeded changelogs around it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Any


@dataclass(frozen=True)
class PublicDatasetRecipe:
    name: str
    public_source: str
    source_family: str
    expected_fields: str
    lift: str
    oracle: str
    license_note: str
    risk: str


RECIPES: tuple[PublicDatasetRecipe, ...] = (
    PublicDatasetRecipe(
        name="FinQA / TAT-QA / MultiHiertt",
        public_source="Hugging Face or official GitHub/project pages",
        source_family="financial reports + tables + gold arithmetic programs",
        expected_fields="report text, tables, question, answer/program/support facts",
        lift="convert the financial table into a ledger; inject restatements, reclassifications, segment moves, footnote corrections, and Unicode-friction entity IDs",
        oracle="apply ledger operations in Python and grade final cents/ratio JSON exactly",
        license_note="check dataset-specific license before redistributing derived prompts",
        risk="models may memorize raw Q&A; procedural lift prevents direct lookup",
    ),
    PublicDatasetRecipe(
        name="TabFact / WikiTableQuestions / SpreadsheetBench",
        public_source="official GitHub/HF/project pages",
        source_family="semi-structured tables and spreadsheet workflows",
        expected_fields="table rows/cells, natural-language statements/questions, spreadsheet files where available",
        lift="turn the table into a mutable business sheet; apply row/cell changelogs, copy/fill/swap/relabel operations, then ask for exact final rows/cells",
        oracle="run table/spreadsheet mutation engine; exact JSON cell/row snapshot",
        license_note="do not package third-party tables unless license permits",
        risk="yes/no table-facts are too low entropy; prefer final-state snapshots",
    ),
    PublicDatasetRecipe(
        name="CUAD / ContractNLI / LEDGAR / Material Contracts Corpus",
        public_source="Atticus, Stanford, SEC/EDGAR-derived corpora",
        source_family="contract clauses, evidence spans, legal metadata",
        expected_fields="contract text, clause labels, evidence spans, hypothesis labels",
        lift="extract real clauses, then generate amendment/redline logs, definition renames, exceptions, survival clauses, and cross-reference edits",
        oracle="apply text edits over clauses and grade selected final clauses or normalized risk fields exactly",
        license_note="CUAD is CC BY 4.0; other corpora vary and may require attribution or source-linking",
        risk="span extraction alone is now too easy; amendment replay creates the long-horizon failure mode",
    ),
    PublicDatasetRecipe(
        name="CORD / SROIE / DocVQA",
        public_source="official GitHub/RRC/DocVQA challenge pages",
        source_family="receipts, invoices, forms, OCR boxes, semantic labels",
        expected_fields="OCR text, bounding boxes, semantic labels, totals, dates, merchant fields",
        lift="convert OCR lines to item ledger; inject OCR corrections, voids, category changes, coupons, tax/fee adjustments, and confusable line IDs",
        oracle="compute final per-category totals, merchant/date fields, or reconciliation exceptions exactly",
        license_note="challenge datasets often allow research use; confirm before redistribution",
        risk="visual OCR is not needed for no-tool GPT endpoint; use OCR text and annotations as substrate",
    ),
    PublicDatasetRecipe(
        name="CRUXEval / LiveCodeBench / CodeNet",
        public_source="official GitHub/HF/project pages",
        source_family="programs with executable input/output labels",
        expected_fields="source code, inputs, expected outputs/tests",
        lift="translate or wrap code into long trace programs; inject variable/string confusables and seeded event streams; ask for output or final state",
        oracle="run the program/trace locally in a sandbox and grade output exactly",
        license_note="check each code corpus license; generated traces are easiest to redistribute",
        risk="avoid cryptographic/hash tasks that are merely impossible without tools rather than diagnostic",
    ),
    PublicDatasetRecipe(
        name="SWE-bench / SWE-bench Verified / SWE-bench Pro Public",
        public_source="official SWE-bench datasets/leaderboards",
        source_family="real GitHub issues, patches, tests, repos",
        expected_fields="issue, repo snapshot, tests, patch/eval harness",
        lift="compress a real issue into a patch-manifest replay: line edits, rebase conflicts, path normalization, final selected file snapshots or test-relevant code output",
        oracle="apply patch queue or run existing tests; exact file snapshot or pass/fail harness",
        license_note="repo licenses vary; prefer adapter that downloads repos rather than redistributing code",
        risk="full SWE-bench requires tools; patch-manifest lift keeps no-tool models comparable",
    ),
    PublicDatasetRecipe(
        name="LogHub / LogHub-2.0",
        public_source="LogPAI GitHub repositories",
        source_family="real system logs across distributed systems, OS, mobile, supercomputers",
        expected_fields="raw log lines, templates, parameters, labels where available",
        lift="turn logs into incident state replay: open/ack/escalate/resolve/reopen, host/service correlation, deduplication, confusable IDs",
        oracle="replay incident state machine and exact-grade open incidents/root-cause fields",
        license_note="some logs are research/academic; avoid packaging raw production logs without checking terms",
        risk="classification of anomaly/no-anomaly is too low entropy; replay state is harder",
    ),
)


def recipe_names() -> list[str]:
    return [r.name for r in RECIPES]


def select_recipes(keyword: str) -> list[PublicDatasetRecipe]:
    k = keyword.lower()
    return [r for r in RECIPES if k in r.name.lower() or k in r.source_family.lower() or k in r.lift.lower()]


def generic_public_lift(record: Mapping[str, Any], *, lift_name: str) -> dict[str, Any]:
    """Placeholder contract for real adapters.

    A concrete adapter should:
      1. Validate the third-party record schema and license/attribution metadata.
      2. Extract a realistic mutable state: table, clauses, file lines, log entities, receipt rows, etc.
      3. Generate a seeded changelog calibrated to ~1,500+ atomic operations for GPT-5.5-hard items.
      4. Run the deterministic oracle.
      5. Return a SUPERCUTE scenario dict.

    We raise NotImplementedError instead of silently creating fake labels.
    """
    raise NotImplementedError(f"No concrete adapter registered for {lift_name!r}; use scenarios_publiclift.py as executable templates.")
