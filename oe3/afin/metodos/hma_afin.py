#!/usr/bin/env python3
"""[Copia del agente afin con --afin y --extra]
Envoltorio para llamar a HMA (original o HMA-LD) desde bench.py.

Uso:
  python3 metodos/hma.py --bin BIN --instancia RUTA --salida ARCHIVO --tiempo T --semilla S
                         [--beta B --rho R] [--reparar] [--beta-rep B --rho-rep R]

- Elige los parámetros de HMA del README según el tamaño (pequeñas: 5/10/15
  clientes; medianas: 100 clientes), con --runs 1 y --random_seed S.
- HMA escribe su archivo con nombre propio y en modo "append"; este
  envoltorio lo corre en un directorio temporal y copia el resultado a --salida.
- --beta/--rho se pasan al binario solo si se indican (el binario original no
  los acepta).
- --reparar: aplica después la reparación mínima de common/consumo_carga.py
  (invertir la ruta, o insertar una estación, o invertir + insertar) a cada
  ruta que no sea factible con consumo según la carga (beta-rep, rho-rep), y
  reescribe la solución en formato HMA con el costo recalculado.
"""
import argparse, os, shutil, subprocess, sys, tempfile, glob

COMMON = "/home/user/oe3/common"
sys.path.insert(0, COMMON)

PEQ = ("--pruning --g_1 20 --pop_size 9 --init rcrs --cross_repair regret --parent_selection circle "
       "--replacement one_on_one --O_1_eval --two_opt --two_opt_star --or_opt 2 --two_exchange 2 --elo 1 "
       "--related_removal --removal_lower 0.2 --removal_upper 0.4 --regret_insertion --individual_search "
       "--population_search --parallel_insertion --conservative_local_search --aggressive_local_search "
       "--station_range 1.0 --subproblem_range 1")
MED = ("--pruning --g_1 20 --pop_size 4 --init rcrs --cross_repair regret --parent_selection circle "
       "--replacement one_on_one --O_1_eval --two_opt --two_opt_star --or_opt 2 --two_exchange 2 --elo 1 "
       "--related_removal --removal_lower 0.1 --removal_upper 0.2 --regret_insertion --individual_search "
       "--population_search --parallel_insertion --conservative_local_search --aggressive_local_search "
       "--station_range 0.5 --subproblem_range 1")


def escribir_solucion(path, I, rutas):
    """Escribe rutas (listas de ids) en el formato de salida de HMA."""
    lineas = ["Details of the solution:"]
    D = 0.0
    for k, r in enumerate(rutas):
        d = sum(I.dist[r[i], r[i + 1]] for i in range(len(r) - 1)); D += d
        lineas.append(f"route {k}, node_num {len(r)}, cost {d:.6f}, nodes: " + " ".join(map(str, r)))
    lineas.append(f"vehicle (route) number: {len(rutas)}")
    lineas.append(f"Total cost: {I.mu1 * len(rutas) + I.mu2 * D:.2f}")
    open(path, "w").write("\n".join(lineas) + "\n")


def reparar(sol_in, sol_out, inst, beta, rho):
    # importa la reparación de common/consumo_carga.py sin ejecutar su main
    argv = sys.argv; sys.argv = ["consumo_carga.py", ""]
    import consumo_carga as cc
    sys.argv = argv
    from evrp import read_instance, read_solution, eval_route
    I = read_instance(inst)
    R, _ = read_solution(sol_in)
    nuevas, stats = [], {"ok": 0, "invertir": 0, "estacion": 0, "invertir+estacion": 0, "sin_reparar": 0}
    for r in R:
        nodes = [x[0] for x in r]
        if eval_route(I, nodes, beta, rho)["feasible"]:
            nuevas.append(nodes); stats["ok"] += 1; continue
        rp = cc.repair(I, nodes, beta, rho)
        if rp is None:
            nuevas.append(nodes); stats["sin_reparar"] += 1
        else:
            nuevas.append(rp[1]); stats[rp[0]] += 1
    escribir_solucion(sol_out, I, nuevas)
    print("reparación:", stats, file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--instancia", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--tiempo", type=int, required=True)
    ap.add_argument("--semilla", type=int, required=True)
    ap.add_argument("--beta", type=float)
    ap.add_argument("--rho", type=float)
    ap.add_argument("--reparar", action="store_true")
    ap.add_argument("--beta-rep", type=float, default=0.2)
    ap.add_argument("--rho-rep", type=float, default=0.0)
    ap.add_argument("--log", help="guardar la salida estándar de HMA aquí")
    ap.add_argument("--afin", type=int, default=None, help="0 = HMA-LD, 1 = inserción afín + respaldo PSSI, 2 = solo afín")
    ap.add_argument("--g1", type=int, default=None, help="reemplaza --g_1 (generaciones sin mejora para terminar)")
    ap.add_argument("--extra", default="", help="parámetros extra para el binario")
    a = ap.parse_args()

    nombre = os.path.basename(a.instancia).rsplit(".", 1)[0]
    params = MED if nombre.endswith("_21") else PEQ
    if a.g1 is not None: params = params.replace("--g_1 20", "--g_1 %d" % a.g1)
    tmp = tempfile.mkdtemp(prefix="hma_")
    try:
        cmd = [a.bin, "--problem", a.instancia, "--time", str(a.tiempo), "--runs", "1",
               "--random_seed", str(a.semilla)] + params.split() + ["--output", tmp + "/"]
        if a.beta is not None: cmd += ["--beta", repr(a.beta)]
        if a.rho is not None: cmd += ["--rho", repr(a.rho)]
        if a.afin is not None: cmd += ["--afin", str(a.afin)]
        cmd += a.extra.split()
        log = open(a.log, "w") if a.log else subprocess.DEVNULL
        rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT)
        fs = glob.glob(os.path.join(tmp, nombre + "_timelimit=*"))
        if not fs:
            print(f"HMA no produjo solución (código {rc})", file=sys.stderr)
            sys.exit(1)
        if a.reparar:
            reparar(fs[0], a.salida, a.instancia, a.beta_rep, a.rho_rep)
        else:
            shutil.copy(fs[0], a.salida)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
