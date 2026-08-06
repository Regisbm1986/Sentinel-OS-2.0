import subprocess
import shutil
import os


class DevOpsAgent:

    def check_services(self):

        services = {}

        ports = {
            "FastAPI": 8000,
            "Streamlit": 8501,
            "SSH": 22
        }

        try:

            result = subprocess.run(
                ["ss", "-tulpn"],
                capture_output=True,
                text=True
            )

            output = result.stdout

            for name, port in ports.items():
                services[name] = str(port) in output

        except Exception:

            services = {
                "FastAPI": False,
                "Streamlit": False,
                "SSH": False
            }

        return services

    def check_disk(self):

        total, used, free = shutil.disk_usage("/")

        return {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2)
        }

    def check_uptime(self):

        try:

            with open("/proc/uptime") as f:

                uptime_seconds = float(
                    f.readline().split()[0]
                )

            return round(
                uptime_seconds / 3600,
                2
            )

        except Exception:

            return 0

    def daily_report(self):

        return {
            "agent": "DevOpsAgent",
            "services": self.check_services(),
            "disk": self.check_disk(),
            "uptime_hours": self.check_uptime()
        }
