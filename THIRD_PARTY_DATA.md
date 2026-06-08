# Third-party data and licenses

SUPERCUTE includes deterministic synthetic generators and small derived benchmark/evaluation artifacts. PublicLift is designed to reuse public datasets as substrates without redistributing their raw records by default.

Before publishing prompts derived from a public dataset, verify the dataset license and attribution requirements. Relevant source families include FinQA, TAT-QA, TabFact, WikiTableQuestions, SpreadsheetBench, CRUXEval, SWE-bench, CUAD, ContractNLI, CORD, SROIE, DocVQA, and LogHub.

The release contains the original experiment artifacts supplied with the project under `data/`. Some files are derived from public benchmark records fetched by the included `fetch_*` scripts. Re-run those scripts against official sources when preparing a formal archival release, and replace or remove derived data if a target venue requires stricter redistribution controls.
