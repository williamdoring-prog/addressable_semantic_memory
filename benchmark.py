"""
Builds/runs the same conceptual ASM sample in Python, C, Rust, and Go.
Each implementation owns the same sample data internally; this runner measures
process-level elapsed time and reports the implementation's internal BENCHMARK_NS.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run_command(name, command):
    start = time.perf_counter_ns()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter_ns() - start

    if proc.returncode != 0:
        return {
            "implementation": name,
            "status": "ERROR",
            "process_ns": elapsed,
            "error": proc.stderr.strip() or proc.stdout.strip(),
        }

    internal = None
    for line in proc.stderr.splitlines():
        if line.startswith("BENCHMARK_NS "):
            internal = int(line.split()[1])

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {"raw_output": proc.stdout.strip()}

    return {
        "implementation": name,
        "status": "OK",
        "process_ns": elapsed,
        "internal_ns": internal,
        "result": result,
    }

def find_go_command():
    """The go binary must match the GOROOT it uses. PATH may resolve to an
    older copy (e.g. a bundled msys2 Go) while GOROOT points at a newer
    install, so prefer the go/gexe inside GOROOT when it exists."""
    goroot = os.environ.get("GOROOT")
    if goroot:
        candidate = Path(goroot) / "bin" / ("go.exe" if sys.platform == "win32" else "go")
        if candidate.exists():
            return str(candidate)
    return "go"

def build():
    commands = []

    if shutil.which("gcc"):
        commands.append((
            "C",
            ["gcc", "-O2", "-std=c11", "asm_c_main.c", "asm_c.c", "-o",
             "asm_c.exe" if sys.platform == "win32" else "asm_c"],
            None,
        ))
    if shutil.which("rustc"):
        # The windows-msvc host needs Visual Studio Build Tools; fall back to
        # the windows-gnu target (bundled linker) when the MSVC linker is missing.
        commands.append((
            "Rust",
            ["rustc", "-O", "asm_main.rs", "-o",
             "asm_rust.exe" if sys.platform == "win32" else "asm_rust"],
            ["--target", "x86_64-pc-windows-gnu"],
        ))
    if shutil.which("go"):
        commands.append((
            "Go",
            [find_go_command(), "build", "-o",
             "asm_go.exe" if sys.platform == "win32" else "asm_go",
             "asm.go", "asm_main.go"],
            None,
        ))

    errors = {}
    for name, cmd, fallback in commands:
        print(f"Building {name}...")
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0 and fallback is not None:
            print(f"  {name} default build failed, retrying with {' '.join(fallback)}...")
            proc = subprocess.run(cmd + fallback, cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            errors[name] = proc.stderr.strip() or proc.stdout.strip() or "build failed"
            print(f"  {name} build failed:\n{errors[name]}")
    return errors

def main():
    build_errors = {}
    if "--build" in sys.argv:
        build_errors = build()

    executables = {
        "C": ROOT / ("asm_c.exe" if sys.platform == "win32" else "asm_c"),
        "Rust": ROOT / ("asm_rust.exe" if sys.platform == "win32" else "asm_rust"),
        "Go": ROOT / ("asm_go.exe" if sys.platform == "win32" else "asm_go"),
    }

    results = []

    # Python implementation is run in-process for direct algorithm timing.
    from asm import ASM, Fragment
    fragments = [
        Fragment("architecture", "ASM uses deterministic retrieval and bounded context assembly."),
        Fragment("memory", "Persistent memory should preserve important project state across sessions."),
        Fragment("retrieval", "Retrieval ranks relevant fragments using question term overlap."),
        Fragment("voice", "Voice output should remain responsive and interruptible."),
        Fragment("safety", "Snapshots validation and rollback protect autonomous project changes."),
        Fragment("research", "Research agents can investigate new techniques and report evidence."),
    ]
    asm = ASM()
    start = time.perf_counter_ns()
    result = asm.run(
        "How does ASM retrieve relevant context and keep the context bounded?",
        fragments,
        28,
    )
    json.dumps(result)  # serialization is part of the timed scope everywhere
    internal = time.perf_counter_ns() - start
    results.append({
        "implementation": "Python",
        "status": "OK",
        "process_ns": internal,
        "internal_ns": internal,
        "result": result,
    })

    for name, executable in executables.items():
        if executable.exists():
            entry = run_command(name, [str(executable)])
            if name in build_errors:
                entry["warning"] = "Build failed; this may be a stale executable from an earlier build."
            results.append(entry)
        elif name in build_errors:
            results.append({
                "implementation": name,
                "status": "ERROR",
                "error": build_errors[name],
            })
        else:
            results.append({
                "implementation": name,
                "status": "SKIPPED",
                "error": "Executable not found. Run: python benchmark.py --build",
            })

    print("\nASM MULTI-LANGUAGE BENCHMARK")
    print("=" * 72)
    print(f"{'Implementation':<16} {'Status':<10} {'Internal ns':>16} {'Process ns':>16}")
    print("-" * 72)

    for item in results:
        internal = str(item.get("internal_ns", "-"))
        process = str(item.get("process_ns", "-"))
        print(f"{item['implementation']:<16} {item['status']:<10} {internal:>16} {process:>16}")

    print("\nALGORITHM OUTPUT CHECK")
    print("-" * 72)
    baseline = None
    for item in results:
        if item["status"] != "OK":
            continue
        value = item.get("result", {})
        if baseline is None:
            baseline = value
            print(f"{item['implementation']}: reference")
        elif value == baseline:
            print(f"{item['implementation']}: MATCH")
        else:
            print(f"{item['implementation']}: DIFFERENT")
            print(json.dumps(value, indent=2))

if __name__ == "__main__":
    main()
