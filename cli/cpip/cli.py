#!/usr/bin/env python3
"""cpip CLI - minimal, dependency-free implementation using argparse.

Features:
- config (list, show, use, edit, import)
- loop (run harness script repeatedly)
- costs (estimate, report)
- cache clean
- alias/union/encrypt placeholders

Config file: ~/.cpip/config.yaml (YAML preferred) or ~/.cpip/config.json as fallback
"""

from __future__ import annotations
import argparse
import os
import sys
import subprocess
import threading
import time
import tempfile
import json
from pathlib import Path
from typing import Any, Dict, List

HOME = Path(os.environ.get("HOME", "."))
CPIP_DIR = HOME / ".cpip"
CONFIG_YAML = CPIP_DIR / "config.yaml"
CONFIG_JSON = CPIP_DIR / "config.json"
CACHE_DIR = CPIP_DIR / "cache"
COSTS_DIR = CPIP_DIR / "costs"

try:
    import yaml  # type: ignore
    YAML_AVAILABLE = True
except Exception:
    YAML_AVAILABLE = False


def ensure_dirs() -> None:
    CPIP_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    COSTS_DIR.mkdir(parents=True, exist_ok=True)


def read_config() -> Dict[str, Any]:
    ensure_dirs()
    if CONFIG_YAML.exists() and YAML_AVAILABLE:
        with open(CONFIG_YAML, "r") as f:
            return yaml.safe_load(f) or {}
    if CONFIG_JSON.exists():
        with open(CONFIG_JSON, "r") as f:
            return json.load(f)
    return {}


def write_config(cfg: Dict[str, Any]) -> None:
    ensure_dirs()
    if YAML_AVAILABLE:
        with open(CONFIG_YAML, "w") as f:
            yaml.safe_dump(cfg, f)
    else:
        with open(CONFIG_JSON, "w") as f:
            json.dump(cfg, f, indent=2)


def cmd_config(args: argparse.Namespace) -> None:
    cfg = read_config()
    profiles: List[Dict[str, Any]] = cfg.get("profiles", [])
    current = cfg.get("current")
    if args.action == "list":
        if not profiles:
            print("No profiles configured. Use 'cpip config edit' to create one.")
            return
        for p in profiles:
            marker = "*" if p.get("name") == current else " "
            print(f"{marker} {p.get('name')} ({p.get('type')})")
    elif args.action == "show":
        name = args.name
        for p in profiles:
            if p.get("name") == name:
                print(json.dumps(p, indent=2))
                return
        print(f"Profile not found: {name}")
    elif args.action == "use":
        name = args.name
        for p in profiles:
            if p.get("name") == name:
                cfg["current"] = name
                write_config(cfg)
                print(f"Set current profile to {name}")
                return
        print(f"Profile not found: {name}")
    elif args.action == "edit":
        # open temp file with current config and open editor
        ensure_dirs()
        if YAML_AVAILABLE and CONFIG_YAML.exists():
            src = CONFIG_YAML
        elif CONFIG_JSON.exists():
            src = CONFIG_JSON
        else:
            # create default config
            cfg = {
                "current": "local-gpu",
                "profiles": [
                    {"name": "local-gpu", "type": "local", "device": "cuda:0", "max_workers": 1}
                ],
            }
            write_config(cfg)
            src = CONFIG_YAML if YAML_AVAILABLE else CONFIG_JSON
        editor = os.environ.get("EDITOR", "vi")
        subprocess.run([editor, str(src)])
        print(f"Edited config: {src}")
    elif args.action == "import":
        path = Path(args.path)
        if not path.exists():
            print(f"Import file not found: {path}")
            return
        # Try to parse import file as YAML or JSON
        data = None
        if YAML_AVAILABLE:
            try:
                with open(path, "r") as f:
                    data = yaml.safe_load(f)
            except Exception:
                pass
        if data is None:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
            except Exception:
                print("Failed to parse import file (yaml/json)")
                return
        # merge profiles
        cfg.setdefault("profiles", [])
        cfg_profiles = cfg["profiles"]
        for p in data.get("profiles", []):
            if not any(x.get("name") == p.get("name") for x in cfg_profiles):
                cfg_profiles.append(p)
        write_config(cfg)
        print(f"Imported config from {path}")
    else:
        print("Unsupported config action")


def run_harness(script: str, run_id: str, iteration: int, profile: str) -> Dict[str, Any]:
    """Run the harness script as a subprocess and capture JSON output if provided."""
    env = os.environ.copy()
    env["CPIP_RUN_ID"] = run_id
    env["CPIP_PROFILE"] = profile
    env["CPIP_ITERATION"] = str(iteration)
    try:
        proc = subprocess.run([sys.executable, script], capture_output=True, text=True, env=env, timeout=3600)
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        return {"exit_code": proc.returncode, "stdout": out, "stderr": err}
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": "timeout"}


def worker_loop(script: str, runs: int, profile: str, results: List[Dict[str, Any]], worker_id: int) -> None:
    run_id = f"run-{int(time.time())}-{worker_id}"
    for i in range(runs):
        res = run_harness(script, run_id, i + 1, profile)
        results.append({"worker": worker_id, "iteration": i + 1, "result": res})


def cmd_loop(args: argparse.Namespace) -> None:
    profile = args.profile or read_config().get("current", "local-gpu")
    script = args.script
    iterations = int(args.iterations or 1)
    concurrency = int(args.concurrency or 1)
    if not Path(script).exists():
        print(f"Script not found: {script}")
        return
    ensure_dirs()
    results: List[Dict[str, Any]] = []
    # divide iterations across workers
    per_worker = (iterations + concurrency - 1) // concurrency
    threads = []
    for w in range(concurrency):
        t = threading.Thread(target=worker_loop, args=(script, per_worker, profile, results, w + 1))
        t.start()
        threads.append(t)
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("Interrupted")
    # write run report
    ts = int(time.time())
    report_path = COSTS_DIR / f"run-report-{ts}.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Run completed. Report: {report_path}")


def cmd_costs(args: argparse.Namespace) -> None:
    cfg = read_config()
    profiles = {p.get("name"): p for p in cfg.get("profiles", [])}
    if args.action == "estimate":
        profile = args.profile or cfg.get("current")
        if profile not in profiles:
            print(f"Profile not found: {profile}")
            return
        p = profiles[profile]
        duration_h = float(args.duration_hours or 1.0)
        workers = int(args.workers or 1)
        # basic pricing: look for pricing.gpu_price_per_hour or pricing.vram_gb_price_per_hour
        pricing = p.get("pricing", {})
        gpu_price = pricing.get("gpu_price_per_hour") or pricing.get("vram_gb_price_per_hour") or pricing.get("gpu_price") or 0.0
        est = float(gpu_price) * workers * duration_h
        print("Profile:", profile)
        print("Workers:", workers)
        print(f"Duration: {duration_h}h")
        print(f"GPU price (per hour): ${gpu_price}")
        print(f"Estimated cost: ${est:.2f}")
    elif args.action == "report":
        run_id = args.run_id
        # find report in COSTS_DIR matching run_id
        found = list(COSTS_DIR.glob(f"*{run_id}*.json"))
        if not found:
            print("Run report not found")
            return
        for fpath in found:
            with open(fpath, "r") as f:
                data = json.load(f)
            print(f"Report: {fpath}")
            print(json.dumps(data, indent=2))
    else:
        print("Unsupported costs action")


def cmd_cache(args: argparse.Namespace) -> None:
    ensure_dirs()
    if args.action == "clean":
        # delete cache contents
        for p in CACHE_DIR.iterdir():
            try:
                if p.is_dir():
                    subprocess.run(["rm", "-rf", str(p)])
                else:
                    p.unlink()
            except Exception as e:
                print("Error removing", p, e)
        print("Cache cleaned")
    else:
        print("Unsupported cache action")


def cmd_alias_union_encrypt(args: argparse.Namespace) -> None:
    print("This command is a placeholder. Features: alias, union, encryption to be implemented in providers or CLI extensions.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cpip")
    subparsers = parser.add_subparsers(dest="cmd")

    # config
    pc = subparsers.add_parser("config", help="Manage cpip config profiles")
    pc.add_argument("action", choices=["list", "show", "use", "edit", "import"], help="action")
    pc.add_argument("name", nargs="?", help="profile name for show/use")
    pc.add_argument("path", nargs="?", help="path to import from")

    # loop
    pl = subparsers.add_parser("loop", help="Run harness script on loop")
    pl.add_argument("script", help="path to harness script")
    pl.add_argument("--profile", help="profile to run on")
    pl.add_argument("--iterations", help="number of iterations to run")
    pl.add_argument("--concurrency", help="parallel workers to use")

    # costs
    pco = subparsers.add_parser("costs", help="Cost estimation and reports")
    pco.add_argument("action", choices=["estimate", "report"], help="action")
    pco.add_argument("--profile", help="profile to estimate for")
    pco.add_argument("--duration-hours", help="duration in hours for estimate")
    pco.add_argument("--workers", help="number of workers for estimate")
    pco.add_argument("--run-id", help="run id for report")

    # cache
    pca = subparsers.add_parser("cache", help="Cache management")
    pca.add_argument("action", choices=["clean"], help="action")

    # alias / union / encrypt placeholder
    paux = subparsers.add_parser("ext", help="alias/union/encryption helpers (placeholder)")
    paux.add_argument("action", nargs="?", help="action")

    return parser


def main(argv: List[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 1
    if args.cmd == "config":
        cmd_config(args)
    elif args.cmd == "loop":
        cmd_loop(args)
    elif args.cmd == "costs":
        cmd_costs(args)
    elif args.cmd == "cache":
        cmd_cache(args)
    elif args.cmd == "ext":
        cmd_alias_union_encrypt(args)
    else:
        print("Unknown command")
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
