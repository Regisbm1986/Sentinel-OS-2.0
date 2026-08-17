import importlib.util
import inspect
import json
import shlex
from dataclasses import dataclass
from pathlib import Path

from sentinel_platform.backend.core.config import MODULES_DIR, PROJECT_ROOT, PYTHON_BIN
from backend.database.capability_registry import CapabilityRegistry


EXECUTION_PARAM_NAMES = {"executor", "logger"}


@dataclass(frozen=True)
class ModuleDefinition:
    key: str
    title: str
    description: str
    mode: str
    fields: tuple
    module_path: str
    function_name: str
    capability_type: str
    route: str


def _load_module_from_path(module_file, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_run_callable(module):
    candidates = []

    for name in sorted(dir(module)):
        if name.startswith("run_"):
            candidate = getattr(module, name)
            if callable(candidate):
                candidates.append((name, candidate))

    if not candidates:
        return None, None

    return candidates[0]


def _infer_mode(signature):
    parameter_names = [parameter.name for parameter in signature.parameters.values()]

    if "executor" in parameter_names:
        return "executor"

    if "logger" in parameter_names:
        return "background"

    return "direct"


def _extract_fields(signature):
    fields = []

    for parameter in signature.parameters.values():
        if parameter.name in EXECUTION_PARAM_NAMES:
            continue

        if parameter.kind not in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            continue

        fields.append(parameter.name)

    return tuple(fields)


def _build_description(module_name, function):
    docstring = inspect.getdoc(function)
    if docstring:
        return docstring.splitlines()[0]

    return f"{module_name.replace('_', ' ').title()} module"


def discover_modules(modules_root=MODULES_DIR, project_root=PROJECT_ROOT):
    discovered = []
    modules_root = Path(modules_root)

    if not modules_root.exists():
        return discovered

    for module_dir in sorted(modules_root.iterdir()):
        if not module_dir.is_dir():
            continue

        module_file = module_dir / "module.py"
        if not module_file.exists():
            continue

        module = _load_module_from_path(
            module_file,
            f"sentinel_discovery_{module_dir.name}",
        )
        if module is None:
            continue

        function_name, function = _get_run_callable(module)
        if function is None:
            continue

        signature = inspect.signature(function)
        fields = _extract_fields(signature)
        mode = _infer_mode(signature)
        route = str(module_file.relative_to(project_root)) if module_file.is_relative_to(project_root) else str(module_file)

        discovered.append(
            ModuleDefinition(
                key=module_dir.name,
                title=module_dir.name.replace("_", " ").title(),
                description=_build_description(module_dir.name, function),
                mode=mode,
                fields=fields,
                module_path=f"backend.modules.{module_dir.name}.module",
                function_name=function_name,
                capability_type=mode,
                route=route,
            )
        )

    return discovered


def sync_capability_registry(registry=None, discovered_modules=None):
    registry = registry or CapabilityRegistry()
    discovered_modules = discovered_modules or discover_modules()

    for module_definition in discovered_modules:
        registry.register_capability(
            module_name=module_definition.key,
            capability_type=module_definition.capability_type,
            route=module_definition.route,
            worker_type=module_definition.mode,
            status="active",
        )

    return discovered_modules


def build_module_command(module_definition, values, project_root=PROJECT_ROOT):
    payload = {field: values.get(field) for field in module_definition.fields}
    payload_json = json.dumps(payload)
    import_path = module_definition.module_path
    function_name = module_definition.function_name
    project_root = Path(project_root)

    if module_definition.mode == "executor":
        script = f"""
import json
import subprocess
import sys
from importlib import import_module

payload = json.loads({payload_json!r})
module = import_module({import_path!r})
function = getattr(module, {function_name!r})

def executor(command, label):
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.stdout:
        print(completed.stdout, end='')
    if completed.stderr:
        print(completed.stderr, end='', file=sys.stderr)
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            command,
            output=completed.stdout,
            stderr=completed.stderr,
        )

result = function(**payload, executor=executor)
if isinstance(result, dict):
    print(json.dumps(result))
    sys.exit(0 if result.get("status") not in {{"error", "failed"}} else 1)

sys.exit(0)
""".strip()
    else:
        script = f"""
import json
import sys
from importlib import import_module

payload = json.loads({payload_json!r})
module = import_module({import_path!r})
function = getattr(module, {function_name!r})
result = function(**payload)
if isinstance(result, dict):
    print(json.dumps(result))
    sys.exit(0 if result.get("status") not in {{"error", "failed"}} else 1)

sys.exit(0)
""".strip()

    return f"cd {shlex.quote(str(project_root))} && {PYTHON_BIN} -c {shlex.quote(script)}"


def build_module_task(module_definition, values, project_root=PROJECT_ROOT):
    missing_fields = [field for field in module_definition.fields if not values.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    return {
        "type": "command",
        "module": module_definition.key,
        "goal": f"Execute {module_definition.title} with {', '.join(f'{field}={values.get(field)}' for field in module_definition.fields)}",
        "command": build_module_command(module_definition, values, project_root=project_root),
        "inputs": {field: values.get(field) for field in module_definition.fields},
    }


def get_module_definition(module_key, modules_root=MODULES_DIR, project_root=PROJECT_ROOT):
    for module_definition in discover_modules(modules_root=modules_root, project_root=project_root):
        if module_definition.key == module_key:
            return module_definition

    return None
