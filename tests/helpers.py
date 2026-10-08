import os
import tempfile
import unittest


class ScratchCase(unittest.TestCase):
    """Runs each test against an empty scratch data folder and a fixed clock."""

    def setUp(self):
        self._home = tempfile.TemporaryDirectory()
        self._env = {k: os.environ.get(k) for k in ("INTAKE_HOME", "INTAKE_NOW")}
        os.environ["INTAKE_HOME"] = self._home.name
        os.environ["INTAKE_NOW"] = "2026-10-07T14:00:00+00:00"

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._home.cleanup()

    def at(self, when: str):
        os.environ["INTAKE_NOW"] = when


def request(**overrides):
    base = {
        "legal_name": "Brightline Analytics, Inc.",
        "website": "https://brightline-analytics.example",
        "touches_customer_data": "yes",
        "business_owner": "Priya Shah",
        "target_start_date": "2026-10-19",
        "requester": "Priya Shah",
        "requester_manager": "Dan Ortiz",
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}
