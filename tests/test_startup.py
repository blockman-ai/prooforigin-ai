import unittest


class StartupTests(unittest.TestCase):
    def test_app_imports_without_heavy_engine_init(self):
        from api.main import app

        self.assertEqual(app.title, "ProofOrigin AI API")

    def test_health_route_registered(self):
        from api.main import app

        paths = {route.path for route in app.routes if hasattr(route, "path")}
        self.assertIn("/health", paths)
        self.assertIn("/", paths)

    def test_runtime_dirs_helper(self):
        import tempfile
        import os
        from api import runtime

        original_dirs = runtime.RUNTIME_DATA_DIRS
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime.RUNTIME_DATA_DIRS = (
                os.path.join(tmpdir, "data"),
                os.path.join(tmpdir, "data", "evidence"),
            )
            try:
                runtime.ensure_runtime_dirs()
                self.assertTrue(os.path.isdir(os.path.join(tmpdir, "data", "evidence")))
            finally:
                runtime.RUNTIME_DATA_DIRS = original_dirs


if __name__ == "__main__":
    unittest.main()
