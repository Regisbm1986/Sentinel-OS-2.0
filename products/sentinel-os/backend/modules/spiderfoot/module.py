import os
import sys

from sentinel_platform.backend.core.config import PYTHON_BIN, SPIDERFOOT_SCRIPT

def run_spiderfoot(target, executor):

    if target:

        sf_script = SPIDERFOOT_SCRIPT

        if os.path.exists(sf_script):

            cmd_sf = [
                str(PYTHON_BIN),
                str(sf_script),
                "-t", "ALL",
                "-u", "all",
                "-q",
                "-s", target
            ]

            executor(cmd_sf, "SpiderFoot-OSINT")

        else:
            print("SpiderFoot não encontrado no servidor.")

    else:
        print("Nenhum alvo especificado.")
