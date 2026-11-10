"""Pure routing advice from declared requirements and capability observations.

This module never executes, authorizes, uploads, provisions, or calls a provider.
All input booleans are unverified claims, including execution_authorized.
"""
import argparse
from datetime import datetime, timezone
import json
import sys

from handoff import load
from safe_io import LedgerError

MAX_SNAPSHOT_AGE_SECONDS = 900
PREFLIGHT = [
    "This plan grants no execution authorization; recheck the scoped user permission before execution.",
    "Before remote dispatch, verify live provider/environment/repository IDs and runtime compatibility.",
    "Before remote dispatch, verify current budget and billing permission; preparation is not spending permission.",
    "Review the explicit input/output allowlists and ensure the remote unit excludes local private state.",
]


def exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"Invalid {label} fields")


def bools(value, names, label):
    if any(type(value[name]) is not bool for name in names):
        raise ValueError(f"Invalid {label} boolean")


def plan(task, capabilities, *, now):
    """Return advisory route/provider/reasons/gates without modifying inputs.

    linux_reproducible refers to the separable remote unit when one is declared;
    otherwise it refers to the whole task. repo_match is the observed binding of
    this task to the selected Codex Cloud environment, not a configured repo name.
    The caller supplies timezone-aware `now` so this function stays deterministic.
    """
    task_flags = {"local_ui", "local_private_state", "remote_separable", "linux_reproducible"}
    exact_keys(task, task_flags | {"os"}, "task")
    bools(task, task_flags, "task")
    if not isinstance(task["os"], str) or task["os"] not in {"linux", "windows", "macos", "any"}:
        raise ValueError("Unsupported task OS")
    exact_keys(capabilities, {"observed_at", "codex_cloud", "vercel"}, "capability snapshot")
    for provider, fields in (("codex_cloud", {"available", "repo_match", "execution_authorized"}),
                             ("vercel", {"available", "execution_authorized"})):
        exact_keys(capabilities[provider], fields, provider)
        bools(capabilities[provider], fields, provider)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    stamp = capabilities["observed_at"]
    if not isinstance(stamp, str):
        raise ValueError("observed_at must be an ISO timestamp")
    try:
        observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid observed_at timestamp") from exc
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")

    reasons, gates = [], list(PREFLIGHT)
    result = {"route": "local", "provider": None, "reasons": reasons, "gates": gates,
              "advisory_only": True}
    local_bound = task["local_ui"] or task["local_private_state"] or task["os"] in {"windows", "macos"}
    if task["local_ui"]:
        reasons.append("On-machine UI work must remain local.")
    if task["local_private_state"]:
        reasons.append("Work that depends on local private state must remain local.")
    if task["os"] in {"windows", "macos"}:
        reasons.append(f"The declared {task['os']} requirement remains local.")
    if local_bound and not task["remote_separable"]:
        reasons.append("No separable remote unit is declared, so the whole task stays local.")
        return result
    if not task["linux_reproducible"]:
        reasons.append("Linux reproducibility has not been declared for the eligible remote work.")
        gates.append("Demonstrate a Linux-reproducible, dependency-defined remote unit before remote planning.")
        return result
    age = (now - observed).total_seconds()
    if age < -60 or age > MAX_SNAPSHOT_AGE_SECONDS:
        reasons.append("The capability snapshot is stale or implausibly in the future.")
        gates.append("Refresh provider observations within 15 minutes of planning; do not rewrite an old timestamp.")
        return result

    ready = []
    cloud = capabilities["codex_cloud"]
    if not cloud["available"]:
        gates.append("Codex Cloud: observe a live available environment for this task.")
    if not cloud["repo_match"]:
        gates.append("Codex Cloud: verify the task repository matches the live environment.")
    if not cloud["execution_authorized"]:
        gates.append("Codex Cloud: obtain task-scoped execution authorization.")
    if all(cloud.values()):
        ready.append("codex_cloud")
    vercel = capabilities["vercel"]
    if not vercel["available"]:
        gates.append("Vercel: observe an available compatible execution capability.")
    if not vercel["execution_authorized"]:
        gates.append("Vercel: obtain explicit task execution and any required billing authorization.")
    if all(vercel.values()):
        ready.append("vercel")
    if not ready:
        reasons.append("No provider is ready under the declared capability and authorization claims.")
        return result
    selected = ready[0]
    # Keep only the selected provider's gates; an unavailable alternative does not
    # block a plan. Shared preflight still requires live permission/ID/budget checks.
    result["gates"] = list(PREFLIGHT)
    result["provider"] = selected
    result["route"] = "hybrid" if task["remote_separable"] else "cloud"
    reasons.append(f"{selected} is the first eligible provider under the supplied claims.")
    if task["remote_separable"]:
        reasons.append("Only the declared separable Linux-reproducible unit is a remote candidate; retain the remaining work locally.")
    else:
        reasons.append("The whole declared task is a Linux-reproducible remote candidate.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", help="Task requirements JSON")
    parser.add_argument("capabilities", help="Timestamped capability observation JSON")
    args = parser.parse_args()
    print(json.dumps(plan(load(args.task), load(args.capabilities), now=datetime.now(timezone.utc)), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, LedgerError, OSError) as error:
        print(json.dumps({"status": "error", "message": str(error)}), file=sys.stderr)
        sys.exit(2)
