import subprocess


def run_nikto_api(target):

    clean_target = (
        target
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )

    cmd_nikto = [
    "nikto",
    "-h",
    clean_target
]

    try:

        print("EXECUTANDO:", cmd_nikto)

        result = subprocess.run(
            cmd_nikto,
            capture_output=True,
            text=True,
        )

        print("RETORNO:", result.returncode)
        print("STDERR:", result.stderr)
        
        return {
            "status": "success",
            "command": cmd_nikto,
            "target": clean_target,
            "output": result.stdout[:5000],
            "stderr": result.stderr
        }

    except Exception as ex:

        return {
            "status": "error",
            "error": str(ex)
        }
