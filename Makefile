PYTHON ?= python3

.PHONY: setup test demo seed status clean dashboard

setup:
	$(PYTHON) -m pip install -r requirements.txt

test:
	PYTHONPATH=.:tests $(PYTHON) -m unittest discover -s tests -v

demo:
	$(PYTHON) -m intake.demo

# Load three sample requests (incomplete, overdue, approved) for status demos
seed:
	$(PYTHON) -m intake.seed
	-$(PYTHON) -m intake publish

status:
	$(PYTHON) -m intake status

# Clear demo records from vendors/ and packs/ (keeps the folders)
clean:
	find vendors packs -type f ! -name .gitkeep -delete
	-$(PYTHON) -m intake publish

# Rebuild dashboard/data.json locally; open it with: python -m http.server -d dashboard
dashboard:
	INTAKE_NO_PUBLISH=1 $(PYTHON) -c "from intake import dashboard; print(dashboard.export())"
