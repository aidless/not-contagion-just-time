.PHONY: eval check

eval:
	python3 -m pytest tests -q

# Offline: no DMXAPI_KEY / DEEPSEEK_API_KEY. Recomputes the identifiability
# block and fails if README.md drifted.
check: eval
	python3 eval/run_cases.py
	python3 eval/run_cases.py --selftest --json > /tmp/cc-selftest.json
	python3 -c 'import json; p=json.load(open("/tmp/cc-selftest.json")); assert p["passed"]==19 and p["total"]==20 and p["failed"]==1, p'
	rm -rf /tmp/cc-dry
	mkdir -p /tmp/cc-dry
	cd /tmp/cc-dry && env -u DMXAPI_KEY -u DEEPSEEK_API_KEY python3 $(CURDIR)/cc_full_experiment.py --phase 1 --reps 1 --conditions C1 --dry-run > /tmp/cc-dry-out.txt
	python3 -c 'from pathlib import Path; t=Path("/tmp/cc-dry-out.txt").read_text(); assert "offline deterministic mock" in t; assert "401" not in t; assert "Unauthorized" not in t; assert "API fail" not in t'
	env -u DMXAPI_KEY -u DEEPSEEK_API_KEY python3 identifiability.py --check README.md --figures-dir /tmp/cc-id-figs
