PYTHON ?= python

.PHONY: selfcheck test sweep-self paper clean

selfcheck:
	$(PYTHON) -m supercute.selfcheck
	$(PYTHON) -m supercute.sweep --module tok --self
	$(PYTHON) -m supercute.sweep --module realtok --self
	$(PYTHON) -m supercute.sweep --module publiclift --self
	$(PYTHON) -m supercute.sweep --module hard --self

test:
	$(PYTHON) -m unittest

sweep-self:
	$(PYTHON) -m supercute.sweep --module tok --self
	$(PYTHON) -m supercute.sweep --module realtok --self
	$(PYTHON) -m supercute.sweep --module publiclift --self

paper:
	cd paper && latexmk -pdf -interaction=nonstopmode main.tex

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	rm -f paper/*.aux paper/*.bbl paper/*.blg paper/*.fdb_latexmk paper/*.fls paper/*.log paper/*.out paper/*.toc
