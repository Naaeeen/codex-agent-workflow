"""Stage the workflow in a new project directory. Dry-run is the default."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile


def plan(root):
    files = {"AGENTS.md": root / "templates/global-AGENTS.md"}
    for directory, destination in (("skills", ".agents/skills"), ("config/agents-current-schema", ".codex/agents")):
        for source in sorted((root / directory).rglob("*")):
            if source.is_file():
                if source.is_symlink():
                    raise ValueError("Source links must be reviewed before installation.")
                files[str(Path(destination) / source.relative_to(root / directory))] = source
    if len(files) < 3 or any(not file.is_file() for file in files.values()):
        raise ValueError("The kit is incomplete. Use the complete release archive.")
    return files


def install(root, destination, apply=False):
    destination = destination.expanduser().resolve()
    for private_root in (Path.home() / ".codex", Path.home() / ".agents"):
        if destination == private_root or destination.is_relative_to(private_root):
            raise ValueError("Choose a fresh project directory for this project installer.")
    files = plan(root)
    if destination.exists():
        raise ValueError("The destination already exists. Choose a fresh project directory.")
    report = {"mode": "apply" if apply else "preview", "files": sorted(files)}
    if not apply:
        return report
    destination.parent.mkdir(parents=True, exist_ok=True)
    parent = destination.parent.resolve()
    stage = Path(tempfile.mkdtemp(prefix=".workflow-stage-", dir=parent)).resolve()
    if stage.parent != parent:
        raise ValueError("Unexpected staging location.")
    try:
        for relative, source in files.items():
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if destination.exists():
            raise ValueError("The destination was created during installation. Choose another directory.")
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(install(Path(__file__).resolve().parent, args.target, args.apply), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
