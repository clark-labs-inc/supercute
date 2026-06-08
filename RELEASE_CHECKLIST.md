# Release checklist

- [x] Remove local VCS and macOS artifacts from release archive.
- [x] Add package metadata, license, citation, contribution guide, and CI.
- [x] Integrate RealTok and PublicLift into the central registry.
- [x] Preserve supplied raw and summarized evaluation results.
- [x] Add unit tests for graders, generators, and registry coverage.
- [x] Run Python compile check.
- [x] Run pytest.
- [x] Run module self-checks.
- [x] Run full benchmark self-check.
- [x] Write submission-style LaTeX paper.
- [x] Compile and render-verify paper PDF.
- [x] Document third-party dataset reuse policy.

Before public upload, edit the repository URLs in `pyproject.toml` and the author block in `paper/main.tex` if needed.
