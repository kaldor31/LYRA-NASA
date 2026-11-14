def pytest_configure(config):
    # starlette suggests httpx2 instead of httpx; this does not affect TestClient
    config.addinivalue_line("filterwarnings", "ignore:Using `httpx`")
