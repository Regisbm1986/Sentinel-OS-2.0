import subprocess


def run_beef_daemon(logger=None):

    try:

        subprocess.Popen(
            [
                "nohup",
                "beef-xss"
            ],
            stdout=open("/tmp/beef.log", "a"),
            stderr=subprocess.STDOUT
        )

        if logger:
            logger(
                "[🕷️] BeEF iniciado em background."
            )

    except Exception as ex:

        if logger:
            logger(
                f"[-] Falha ao iniciar BeEF: {ex}"
            )
