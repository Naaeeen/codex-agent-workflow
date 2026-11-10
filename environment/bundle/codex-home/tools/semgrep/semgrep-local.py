"""Run pinned Semgrep CE against explicit local rules and local targets only."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--error", action="store_true", help="Return 1 for findings")
    args = parser.parse_args()
    # Reject raw network/device paths before filesystem resolution can contact SMB.
    if str(args.config).startswith(("\\\\", "//")) or str(args.target).startswith(("\\\\", "//")):
        parser.error("UNC/network/device paths are not supported")
    config = args.config.resolve(strict=True)
    target = args.target.resolve(strict=True)
    if not config.is_file() or config.suffix.lower() not in {".yaml", ".yml"}:
        parser.error("--config must name an existing local YAML file")
    # Disallow UNC paths: these can fetch rules or source from network shares.
    if str(config).startswith("\\\\") or str(target).startswith("\\\\"):
        parser.error("UNC/network paths are not supported")
    root = Path(__file__).resolve().parent
    state = root / "state"
    state.mkdir(exist_ok=True)
    env = os.environ.copy()
    for name in list(env):
        if (name.startswith("SEMGREP_") or name.startswith("OTEL_")
                or name in {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE"}):
            del env[name]
    env.update({
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_SETTINGS_FILE": str(state / "settings.yml"),
        "SEMGREP_LOG_FILE": str(state / "semgrep.log"),
        "NO_COLOR": "1",
        "PYTHONNOUSERSITE": "1",
    })
    command = [str(root / "venv" / "Scripts" / "semgrep.exe"), "scan",
               "--oss-only", "--metrics=off", "--disable-version-check",
               "--no-autofix", "--strict", "--json", "--config", str(config)]
    if args.error:
        command.append("--error")
    command.extend(["--", str(target)])
    return subprocess.run(command, env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
