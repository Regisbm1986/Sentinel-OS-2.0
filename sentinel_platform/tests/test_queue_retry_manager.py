import json

import pytest

from sentinel_platform.backend.agents.task_queue import TaskQueue
from sentinel_platform.backend.agents.queue_retry_manager import QueueRetryManager


@pytest.fixture
def temp_queue(tmp_path, monkeypatch):
    queue_dir = tmp_path / "tasks"
    queue_dir.mkdir()

    monkeypatch.setattr("sentinel_platform.backend.agents.task_queue.AGENT_TASKS_DIR", queue_dir)

    queue = TaskQueue()
    queue._ensure_file()

    return queue, queue_dir


def test_queue_retry_manager_requeues_failed_task(temp_queue):
    queue, _ = temp_queue
    manager = QueueRetryManager(queue=queue, max_retries=3, retry_delay_seconds=0)

    task = {"type": "create_file", "path": "notes.txt", "content": "x"}
    queue.add_task(task)

    retry_task = manager.handle_failure(task, {"status": "failed", "error": "boom"})

    assert retry_task["attempts"] == 1
    assert retry_task["retry_at"] is not None
    assert queue.peek_next_task() == retry_task


def test_queue_retry_manager_stops_after_max_retries(temp_queue):
    queue, _ = temp_queue
    manager = QueueRetryManager(queue=queue, max_retries=1, retry_delay_seconds=0)

    task = {"type": "create_file", "path": "notes.txt", "content": "x", "attempts": 1}
    queue.add_task(task)

    result = manager.handle_failure(task, {"status": "failed", "error": "boom"})

    assert result is None
    assert queue.peek_next_task() == task
