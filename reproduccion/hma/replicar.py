"""Descarga una revisión fija de HMA y reproduce su ejemplo pequeño."""
import datetime
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
URL = "https://github.com/0SliverBullet/EVRP-TW-SPD-HMA.git"
COMMIT = "0ebbcaa4c2b8385c2c9bff06d60689cb2c64229d"
LOCAL = ROOT / ".local"
REPO = LOCAL / "upstream"


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def capture(args):
    return subprocess.check_output([str(a) for a in args], text=True).strip()


def main():
    compiler = shutil.which("g++")
    if not compiler or not shutil.which("git"):
        sys.exit("Se requieren git y un compilador g++ compatible con C++11.")
    LOCAL.mkdir(exist_ok=True)
    if not REPO.exists():
        run(["git", "clone", URL, REPO])
        run(["git", "-C", REPO, "checkout", "--detach", COMMIT])
    if capture(["git", "-C", REPO, "rev-parse", "HEAD"]) != COMMIT:
        sys.exit("La revisión local no coincide con la fijada; no se modificó.")
    if capture(["git", "-C", REPO, "status", "--porcelain"]):
        sys.exit("La copia original tiene cambios; preservarlos antes de reproducir.")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "resultados" / stamp
    output.mkdir(parents=True)
    binary = LOCAL / "evrp-tw-spd"
    build = [compiler, "-std=c++11", "-O3", "-o", str(binary)] + [
        str(REPO / "src" / name) for name in (
            "evrp_tw_spd_solver.cpp", "eval.cpp", "operator.cpp",
            "search_framework.cpp", "solution.cpp", "util.cpp", "data.cpp", "evolution.cpp"
        )
    ]
    with (output / "compilacion.log").open("w") as log:
        run(build, stdout=log, stderr=subprocess.STDOUT)
    instance = REPO / "data/akb_instances/c101C5.txt"
    args = [str(binary), "--problem", str(instance), "--output", str(output) + "/"]
    args += """--pruning --time 105 --runs 10 --random_seed 2026
    --g_1 20 --pop_size 9 --init rcrs --cross_repair regret
    --parent_selection circle --replacement one_on_one --O_1_eval
    --two_opt --two_opt_star --or_opt 2 --two_exchange 2 --elo 1
    --related_removal --removal_lower 0.2 --removal_upper 0.4
    --regret_insertion --individual_search --population_search
    --parallel_insertion --conservative_local_search --aggressive_local_search
    --station_range 1.0 --subproblem_range 1""".split()
    metadata = {
        "utc": stamp, "repository": URL, "commit": COMMIT,
        "platform": platform.platform(), "machine": platform.machine(),
        "compiler": capture([compiler, "--version"]),
        "build_command": build, "run_command": args,
        "instance_sha256": hashlib.sha256(instance.read_bytes()).hexdigest(),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "note": "Parámetros del ejemplo pequeño original; semilla inicial explícita 2026. Hardware diferente al artículo.",
    }
    (output / "metadatos.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Ejecutando 10 corridas, límite de 105 segundos por corrida. Resultados: {output}", flush=True)
    with (output / "ejecucion.log").open("w") as log:
        run(args, cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
    solution = output / "c101C5_timelimit=105_subproblem=1.txt"
    if not solution.exists():
        sys.exit("No se generó la solución; revisar ejecucion.log aunque el proceso haya retornado cero.")
    print(solution.read_text())


if __name__ == "__main__":
    main()
