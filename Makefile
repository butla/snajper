run:
	ls snajper/spotter.py | entr -cr python snajper/spotter.py

test_sample:
	PYTHONPATH=tests/sample_project coverage run -m pytest tests/sample_project/tests

db_cli:
	litecli .coverage
