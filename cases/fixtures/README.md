# Case validation fixtures

`valid/ashcroft_manor.json` contains a structurally and semantically valid
minimal case.

Each file under `invalid/` represents one deliberate publication failure.
The filename corresponds to the expected stable validation code.

The unit test factory in `backend/tests/factories/cases.py` mirrors the valid
fixture and is used to construct focused invalid cases without repeating the
entire manifest.