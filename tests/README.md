# Tests

Default pytest tests cover schema validation, PDF checks, restructuring behavior, and a Streamlit render smoke check without external calls. `test_db_integration.py` is opt-in with `RUN_DB_TESTS=1`; it rolls back synthetic rows. Keep fixtures synthetic and avoid personal essays or secrets in tests.
