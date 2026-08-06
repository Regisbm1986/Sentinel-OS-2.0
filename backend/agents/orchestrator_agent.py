from sentinel_os.platform.backend.agents.agent_memory import AgentMemory
from sentinel_os.platform.backend.agents.backend_agent import BackendAgent
from sentinel_os.platform.backend.agents.codex_agent import CodexAgent
from sentinel_os.platform.backend.agents.task_executor import TaskExecutor


class OrchestratorAgent:

    def execute_task(self):

        codex_agent = CodexAgent()

        cycle_result = codex_agent.execute_cycle()

        if cycle_result["status"] == "no_tasks":

            return {
                "status": "no_tasks"
            }

        task = cycle_result["task"]
        plan = cycle_result["plan"]
        review = cycle_result["review"]

        task_executor = TaskExecutor()

        task_executor.execute(task["id"])

        backend_agent = BackendAgent()

        implementation_plan = backend_agent.generate_implementation_plan(
            task
        )

        memory = AgentMemory()

        memory.remember({
            "task_id": task["id"],
            "task": task["task"],
            "status": "completed"
        })

        return {
            "status": "orchestration_completed",
            "task": task,
            "plan": plan,
            "review": review,
            "implementation": implementation_plan
        }
