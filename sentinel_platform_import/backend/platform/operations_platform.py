from sentinel_os.platform.backend.core.config import PROJECT_ROOT
from sentinel_os.platform.backend.modules.beef.module import run_beef_daemon
from sentinel_os.platform.backend.modules.dagda.module import check_dagda_status, run_dagda
from sentinel_os.platform.backend.modules.enum4linux.module import run_enum4linux
from sentinel_os.platform.backend.modules.john.module import run_john_the_ripper
from sentinel_os.platform.backend.modules.kubehunter.module import run_kube_hunter
from sentinel_os.platform.backend.modules.nikto.module import run_nikto_api
from sentinel_os.platform.backend.modules.setoolkit.module import run_setoolkit_daemon
from sentinel_os.platform.backend.modules.spiderfoot.module import run_spiderfoot

from sentinel_os.platform.backend.platform.module_discovery import (
    ModuleDefinition,
    build_module_task,
    discover_modules,
    get_module_definition,
    sync_capability_registry,
)


def get_module_definitions():
    discovered_modules = discover_modules(project_root=PROJECT_ROOT)
    sync_capability_registry(discovered_modules=discovered_modules)
    return discovered_modules


def build_module_execution_task(module_key, values):
    definition = get_module_definition(module_key)

    if definition is None:
        raise ValueError(f"Unsupported module key: {module_key}")

    return build_module_task(definition, values)


def build_module_execution_task_for_queue(module_key, values):
    return build_module_execution_task(module_key, values)


def execute_module(module_key, values, executor=None, logger=None):
    if module_key == "nikto":
        return run_nikto_api(values.get("target"))

    if module_key == "spiderfoot":
        return run_spiderfoot(values.get("target"), executor)

    if module_key == "dagda":
        return run_dagda(values.get("image_name"))

    if module_key == "kubehunter":
        return run_kube_hunter(
            values.get("cluster_ip"),
            executor,
            logger=logger,
            flags_extras=values.get("flags_extras", ""),
        )

    if module_key == "enum4linux":
        return run_enum4linux(values.get("target"), executor)

    if module_key == "john":
        return run_john_the_ripper(values.get("hash_text"), executor, logger=logger)

    if module_key == "beef":
        return run_beef_daemon(logger=logger)

    if module_key == "set":
        return run_setoolkit_daemon(logger=logger)

    raise ValueError(f"Unsupported module key: {module_key}")


def get_dagda_status():
    return check_dagda_status()
