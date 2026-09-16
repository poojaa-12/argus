.PHONY: test eval eval-judge eval-deals up down api install

install:
	python3 -m pip install -e ".[dev]"

test:
	PYTHONPATH=. python3 -m pytest -q

eval:
	PYTHONPATH=. python3 -m argus.evals.report

eval-judge:
	PYTHONPATH=. python3 -m argus.evals.judge.report

eval-deals:
	PYTHONPATH=. python3 -m argus.evals.deals_report

up:
	docker compose up -d

down:
	docker compose down

api:
	PYTHONPATH=. python3 -m uvicorn argus.serving.api:app --reload --port 8080

install:
	python3 -m pip install -e ".[dev]"

test:
	PYTHONPATH=. python3 -m pytest -q

eval:
	PYTHONPATH=. python3 -m argus.evals.report

eval-judge:
	PYTHONPATH=. python3 -m argus.evals.judge.report

up:
	docker compose up -d

down:
	docker compose down

api:
	PYTHONPATH=. python3 -m uvicorn argus.serving.api:app --reload --port 8080
