import backend.api.main as api_main


class FakeRouter:
    def __init__(self, name):
        self.name = name


class FakeModule:
    def __init__(self, router=None):
        self.router = router


def test_register_routes_includes_generated_route_modules(tmp_path, monkeypatch):
    routes_dir = tmp_path / "routes"
    routes_dir.mkdir()

    (routes_dir / "beef.py").write_text("router = object()\n")

    fake_router = FakeRouter("beef")
    imported = {}

    def fake_import_module(module_name):
        imported["module_name"] = module_name
        return FakeModule(router=fake_router)

    monkeypatch.setattr(api_main.importlib, "import_module", fake_import_module)

    app = api_main.FastAPI(title="Test")
    registered = []

    def fake_include_router(router, prefix="/"):
        registered.append((router, prefix))

    app.include_router = fake_include_router

    api_main.register_routes(app, routes_dir=routes_dir, module_prefix="fake.routes")

    assert imported["module_name"] == "fake.routes.beef"
    assert registered == [(fake_router, "/api")]


def test_register_routes_skips_modules_without_router(tmp_path, monkeypatch):
    routes_dir = tmp_path / "routes"
    routes_dir.mkdir()

    (routes_dir / "dummy.py").write_text("value = 42\n")

    def fake_import_module(module_name):
        return FakeModule(router=None)

    monkeypatch.setattr(api_main.importlib, "import_module", fake_import_module)

    app = api_main.FastAPI(title="Test")
    registered = []

    app.include_router = lambda router, prefix="/": registered.append((router, prefix))

    api_main.register_routes(app, routes_dir=routes_dir, module_prefix="fake.routes")

    assert registered == []
