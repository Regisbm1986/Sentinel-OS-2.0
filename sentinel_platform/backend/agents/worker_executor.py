from sentinel_platform.backend.agents.task_result_manager import TaskResultManager
from sentinel_platform.backend.agents.tools.file_tool import FileTool
from sentinel_platform.backend.agents.tools.command_tool import CommandTool


class WorkerExecutor:

    def __init__(self):

        self.results = TaskResultManager()
        self.file_tool = FileTool()
        self.command_tool = CommandTool()

    def execute(self, worker_id, task):

        if isinstance(task, dict):

            task_type = task.get("type")

            if task_type == "create_file":

                result = self.file_tool.create_file(
                    task["path"],
                    task["content"]
                )

            elif task_type == "read_file":

                result = self.file_tool.read_file(
                    task["path"]
                )

            elif task_type == "command":

                result = self.command_tool.execute(
                    task["command"]
                )

            else:

                result = {
                    "status": "unsupported_task"
                }

        else:

            result = {
                "worker_id": worker_id,
                "task_id": task,
                "status": "completed"
            }

        self.results.save_result(
            str(task),
            result
        )

        return result
