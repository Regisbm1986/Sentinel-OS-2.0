from sentinel_platform.backend.agents.goal_planner import GoalPlanner
from sentinel_platform.backend.agents.task_queue import TaskQueue


class DeveloperWorker:

    def __init__(self):

        self.queue = TaskQueue()
        self.planner = GoalPlanner()

    def create_file_task(
        self,
        path,
        content
    ):

        task = {
            "type": "create_file",
            "path": path,
            "content": content
        }

        self.queue.add_task(task)

        return task

    def create_goal(self, goal):

        tasks = self.planner.plan(goal)

        for task in tasks:
            self.queue.add_task(task)

        return tasks
