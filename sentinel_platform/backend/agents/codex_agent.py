import json
import os

from sentinel_platform.backend.core.config import AGENT_TASKS_DIR
from sentinel_platform.backend.agents.agent_controller import AgentController
from sentinel_platform.backend.agents.review_agent import ReviewAgent


class CodexAgent:

    TASK_PATH = AGENT_TASKS_DIR

    def get_approved_tasks(self):

        controller = AgentController()

        return controller.get_approved_tasks()

    def get_next_task(self):

        tasks = self.get_approved_tasks()

        if not tasks:

            return {
                "status": "no_tasks"
            }

        return tasks[0]

    def generate_task_context(self):

        task = self.get_next_task()

        if task == {"status": "no_tasks"}:

            return {
                "status": "no_tasks"
            }

        return {
            "status": "task_ready",
            "task": task,
            "context": {
                "project": "Sentinel OS",
                "agent": "CodexAgent"
            }
        }

    def generate_execution_plan(self):

        task = self.get_next_task()

        if task == {"status": "no_tasks"}:

            return {
                "status": "no_tasks"
            }

        return {
            "status": "plan_ready",
            "task": task,
            "steps": [
                "analyze",
                "implement",
                "review"
            ]
        }

    def generate_review_request(self):

        execution_plan = self.generate_execution_plan()

        if execution_plan["status"] == "no_tasks":

            return {
                "status": "no_tasks"
            }

        task = execution_plan["task"]

        return {
            "status": "review_requested",
            "task": task,
            "plan": execution_plan,
            "review_agent": "ReviewAgent"
        }

    def execute_cycle(self):

        execution_plan = self.generate_execution_plan()

        if execution_plan["status"] == "no_tasks":

            return {
                "status": "no_tasks"
            }

        review_request = self.generate_review_request()

        if review_request["status"] == "no_tasks":

            return {
                "status": "no_tasks"
            }

        review_agent = ReviewAgent()

        review_result = review_agent.consume_review_request(
            review_request
        )

        return {
            "status": "cycle_completed",
            "task": execution_plan["task"],
            "plan": execution_plan,
            "review": review_result
        }
