import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks
from redis.exceptions import ConnectionError

from app.api.analysis import _enqueue_or_run_locally


class AnalysisQueueFallbackTests(unittest.TestCase):
    def test_development_runs_analysis_as_background_task_without_redis(self):
        background_tasks = BackgroundTasks()
        job_id = "a" * 32

        with (
            patch.dict(os.environ, {"APP_ENV": "development"}),
            patch(
                "app.api.analysis.enqueue_analysis",
                side_effect=ConnectionError("Redis is unavailable"),
            ),
            patch("app.api.analysis.process_analysis_job") as process_job,
        ):
            task_id = _enqueue_or_run_locally(job_id, background_tasks)
            self.assertEqual(task_id, f"local-background-{job_id}")
            self.assertEqual(len(background_tasks.tasks), 1)

            asyncio.run(background_tasks())

        process_job.assert_called_once_with(job_id)

    def test_production_does_not_fall_back_when_redis_is_unavailable(self):
        background_tasks = BackgroundTasks()

        with (
            patch.dict(os.environ, {"APP_ENV": "production"}),
            patch(
                "app.api.analysis.enqueue_analysis",
                side_effect=ConnectionError("Redis is unavailable"),
            ),
        ):
            with self.assertRaises(ConnectionError):
                _enqueue_or_run_locally("a" * 32, background_tasks)

        self.assertEqual(background_tasks.tasks, [])


if __name__ == "__main__":
    unittest.main()
