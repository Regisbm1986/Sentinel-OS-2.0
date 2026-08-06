from datetime import datetime, timedelta


class QueueRetryManager:
    def __init__(self, queue, max_retries=3, retry_delay_seconds=60):
        self.queue = queue
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def handle_failure(self, task, result):
        attempts = task.get("attempts", 0) + 1

        if attempts > self.max_retries:
            return None

        retry_task = dict(task)
        retry_task["attempts"] = attempts
        retry_task["retry_at"] = (
            datetime.now() + timedelta(seconds=self.retry_delay_seconds)
        ).isoformat()

        queue_data = self.queue._load()
        updated = False

        for index, queued_task in enumerate(queue_data):
            if queued_task == task:
                queue_data[index] = retry_task
                updated = True
                break

        if not updated:
            queue_data.append(retry_task)
        
        self.queue._save(queue_data)

        return retry_task
