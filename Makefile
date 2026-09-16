.PHONY: preflight selftest demo clean lock
preflight:   ## P0 gate — run this first on the execution plane
	python3 scripts/preflight.py
selftest:    ## P5 acceptance: skeptic must kill planted spurious findings
	python3 tests/test_core.py && python3 tests/test_skeptic_planted.py
demo:        ## offline end-to-end: prereg -> traces -> skeptic -> KB -> digest
	python3 scripts/demo_offline.py
lock:
	pip freeze > requirements.lock
clean:
	rm -rf traces/*.jsonl store state findings/*.yaml negative_results/*.yaml \
	       preregistrations/*.yaml reports/daily/*.md __pycache__ */__pycache__
