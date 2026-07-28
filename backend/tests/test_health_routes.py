import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.interfaces.api import health_routes


class _ConnectionContext:
    def __enter__(self):
        return MagicMock()

    def __exit__(self, exc_type, exc, traceback):
        return False


class HealthRouteTests(unittest.TestCase):
    def test_live_is_process_only(self):
        self.assertEqual(health_routes.live(), {"status": "ok"})

    def test_ready_reports_healthy_dependencies(self):
        qdrant = MagicMock()
        qdrant.get_collections.return_value.collections = [
            MagicMock(name="discrete_math_materials")
        ]
        qdrant.get_collections.return_value.collections[0].name = (
            "discrete_math_materials"
        )
        qdrant.get_collection.return_value.config.params.vectors.size = 4096

        with tempfile.TemporaryDirectory() as storage_dir:
            with (
                patch.object(
                    health_routes.settings,
                    "STORAGE_DIR",
                    storage_dir,
                ),
                patch.object(
                    health_routes.engine,
                    "connect",
                    return_value=_ConnectionContext(),
                ),
                patch.object(
                    health_routes.redis_client.client,
                    "ping",
                    return_value=True,
                ),
                patch.object(
                    health_routes,
                    "get_qdrant_client",
                    return_value=qdrant,
                ),
            ):
                response = health_routes.ready()

        self.assertEqual(response["status"], "ready")
        self.assertTrue(all(response["components"].values()))

    def test_ready_rejects_wrong_qdrant_dimension(self):
        qdrant = MagicMock()
        collection = MagicMock()
        collection.name = "discrete_math_materials"
        qdrant.get_collections.return_value.collections = [collection]
        qdrant.get_collection.return_value.config.params.vectors.size = 1536

        with tempfile.TemporaryDirectory() as storage_dir:
            with (
                patch.object(health_routes.settings, "STORAGE_DIR", storage_dir),
                patch.object(
                    health_routes.engine,
                    "connect",
                    return_value=_ConnectionContext(),
                ),
                patch.object(
                    health_routes.redis_client.client,
                    "ping",
                    return_value=True,
                ),
                patch.object(
                    health_routes,
                    "get_qdrant_client",
                    return_value=qdrant,
                ),
            ):
                response = health_routes.ready()

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.body)
        self.assertFalse(payload["components"]["qdrant"])

    def test_ready_returns_503_without_dependencies(self):
        with tempfile.TemporaryDirectory() as storage_dir:
            with (
                patch.object(
                    health_routes.settings,
                    "STORAGE_DIR",
                    storage_dir,
                ),
                patch.object(
                    health_routes.engine,
                    "connect",
                    side_effect=RuntimeError("mysql unavailable"),
                ),
                patch.object(
                    health_routes.redis_client.client,
                    "ping",
                    side_effect=RuntimeError("redis unavailable"),
                ),
                patch.object(
                    health_routes,
                    "get_qdrant_client",
                    side_effect=RuntimeError("qdrant unavailable"),
                ),
            ):
                response = health_routes.ready()

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.body)
        self.assertEqual(payload["status"], "not_ready")
        self.assertTrue(payload["components"]["storage"])
