import subprocess


class CommandTool:

    def execute(self, command):

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )

        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
