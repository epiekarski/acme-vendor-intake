PYTHON ?= python3

.PHONY: setup test demo seed status clean

setup:
	$(PYTHON) -m pip install -r requirements.txt

test:
	PYTHONPATH=.:tests $(PYTHON) -m unittest discover -s tests -v

demo:
	$(PYTHON) -m intake.demo

# Load three sample requests (incomplete, overdue, approved) for status demos
seed:
	$(PYTHON) -m intake.seed

status:
	$(PYTHON) -m intake status

# Clear demo records from vendors/ and packs/ (keeps the folders)
clean:
	find vendors packs -type f ! -name .gitkeep -delete
