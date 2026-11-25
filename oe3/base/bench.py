#!/usr/bin/env python3
"""Banco de pruebas común del OE3.

Ejecuta un método (comando con plantilla) sobre un conjunto de instancias akb,
con un presupuesto de tiempo y varias semillas, valida cada solución con el
juez oficial (common/evrp.py: check_solution(..., use_reported=False)) y
escribe un CSV por corrida más un resumen por instancia.

Ejemplo:
  python3 bench.py --metodo hma_ld --conjunto conjuntos/desarrollo.txt --semillas 1 2 3 \\
      --cmd 'python3 metodos/hma.py --bin hma-ld/bin/evrp-tw-spd --beta 0.2 --rho 0 \\
             --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'

Marcadores de la plantilla: {instancia} (ruta del .txt de la instancia),
{nombre} (nombre sin extensión), {salida} (archivo que el método DEBE escribir,
en formato de salida de HMA), {tiempo} (segundos, entero), {semilla},
{beta}, {rho}.

Formato de salida exigido (el mismo que escribe HMA; lo lee evrp.read_solution):
    route 0, node_num 7, cost 151.49, nodes: 0 8 5 1 6 4 0
    route 1, node_num 5, cost 106.26, nodes: 0 2 7 3 0
    Total cost: 2257.75
- Una línea por ruta que empiece con "route" y contenga "nodes:"; después de
  "nodes:" van los ids de los nodos separados por espacios, empezando y
  terminando en el depósito 0, con las estaciones donde se visitan. Opcionalmente
  cada nodo puede llevar "(y, Y)" (lo ignora el juez con use_reported=False).
- Una línea "Total cost: X" con TC = mu1*K + mu2*D (tolerancia 0,01).
- El resto de las líneas se ignora. La recarga NO se informa: el juez decide
  el plan de recarga exacto por programa lineal para la secuencia dada.
"""
import argparse, csv, os, resource, shlex, subprocess, sys, time, statistics
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
COMMON = "/home/user/oe3/common"
INST_DIR = os.path.join(COMMON, "hma/data/akb_instances")
sys.path.insert(0, COMMON)
from evrp import read_instance, read_solution, check_solution  # noqa: E402

CAMPOS = ["metodo", "instancia", "n_clientes", "semilla", "tiempo_limite", "factible", "K", "distancia",
          "costo_TC", "energia", "costo_informado", "tiempo_pared", "tiempo_cpu", "codigo_salida", "errores"]


def es_pequena(nombre):
    return not nombre.endswith("_21")


def leer_conjunto(path):
    return [l.strip() for l in open(path) if l.strip() and not l.startswith("#")]


def juzgar(inst_path, sol_path, beta, rho):
    I = read_instance(inst_path)
    if not os.path.exists(sol_path) or os.path.getsize(sol_path) == 0:
        return I, None, "sin archivo de solución"
    try:
        R, total = read_solution(sol_path)
    except Exception as e:  # archivo mal formado
        return I, None, f"no se pudo leer: {e}"
    if not R or total is None:
        return I, None, "sin rutas o sin 'Total cost'"
    return I, check_solution(I, R, total, beta=beta, rho=rho, use_reported=False), None


def correr(a, nombre, semilla, tiempo, sol_dir, log_dir):
    inst = os.path.join(INST_DIR, nombre + ".txt")
    salida = os.path.join(sol_dir, f"{nombre}_s{semilla}.txt")
    if os.path.exists(salida):
        os.remove(salida)
    cmd = a.cmd.format(instancia=inst, nombre=nombre, salida=salida, tiempo=tiempo, semilla=semilla,
                       beta=a.beta, rho=a.rho)
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.time()
    with open(os.path.join(log_dir, f"{nombre}_s{semilla}.log"), "w") as log:
        try:
            p = subprocess.run(cmd, shell=True, stdout=log, stderr=subprocess.STDOUT, cwd=BASE,
                               timeout=a.factor_kill * tiempo + a.margen_kill)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    wall = time.time() - t0
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    I, res, err = juzgar(inst, salida, a.beta, a.rho)
    fila = dict(metodo=a.metodo, instancia=nombre, n_clientes=len(I.customers), semilla=semilla,
                tiempo_limite=tiempo, tiempo_pared=round(wall, 2), tiempo_cpu=round(cpu, 2), codigo_salida=rc)
    if res is None:
        fila.update(factible=0, K="", distancia="", costo_TC="", energia="", costo_informado="", errores=err)
    else:
        _, total = read_solution(salida)
        fila.update(factible=int(res["ok"]), K=res["K"], distancia=round(res["dist"], 4),
                    costo_TC=round(res["cost"], 4), energia=round(res["energy"], 4), costo_informado=total,
                    errores=" | ".join(res["errors"])[:500])
    return fila


def resumir(filas, path_csv, path_md, metodo):
    por = defaultdict(list)
    for f in filas:
        por[f["instancia"]].append(f)
    out = []
    for nombre in sorted(por, key=lambda n: (not es_pequena(n), n)):
        fs = por[nombre]
        fac = [f for f in fs if int(f["factible"]) == 1]
        cost = [float(f["costo_TC"]) for f in fac]
        Ks = [int(f["K"]) for f in fac]
        out.append(dict(metodo=metodo, instancia=nombre, corridas=len(fs), factibles=len(fac),
                        costo_medio=round(statistics.mean(cost), 2) if cost else "",
                        costo_min=round(min(cost), 2) if cost else "",
                        K_medio=round(statistics.mean(Ks), 2) if Ks else "",
                        tiempo_medio=round(statistics.mean(float(f["tiempo_pared"]) for f in fs), 1)))
    with open(path_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    with open(path_md, "w") as fh:
        fh.write(f"| instancia | factibles | costo medio (factibles) | costo mín. | K medio | tiempo medio (s) |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for o in out:
            fh.write(f"| {o['instancia']} | {o['factibles']}/{o['corridas']} | {o['costo_medio']} | "
                     f"{o['costo_min']} | {o['K_medio']} | {o['tiempo_medio']} |\n")
        tot = sum(o["corridas"] for o in out); fac = sum(o["factibles"] for o in out)
        fh.write(f"\nTotal: {fac}/{tot} corridas factibles según el juez oficial.\n")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metodo", required=True, help="nombre del método (carpeta de resultados)")
    ap.add_argument("--cmd", required=True, help="plantilla del comando")
    ap.add_argument("--conjunto", default=os.path.join(BASE, "conjuntos/desarrollo.txt"))
    ap.add_argument("--instancias", nargs="*", help="lista explícita (reemplaza --conjunto)")
    ap.add_argument("--solo", choices=["pequenas", "grandes"], help="filtrar por tamaño")
    ap.add_argument("--semillas", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--t-pequenas", type=int, default=105, help="s para 5/10/15 clientes")
    ap.add_argument("--t-grandes", type=int, default=120, help="s para 100 clientes")
    ap.add_argument("--beta", type=float, default=0.2)
    ap.add_argument("--rho", type=float, default=0.0)
    ap.add_argument("--out", help="carpeta de resultados (por defecto resultados/<metodo>)")
    ap.add_argument("--reanudar", action="store_true", help="no repetir corridas ya presentes en el CSV")
    ap.add_argument("--factor-kill", type=float, default=2.0)
    ap.add_argument("--margen-kill", type=float, default=60.0)
    a = ap.parse_args()

    nombres = a.instancias or leer_conjunto(a.conjunto)
    if a.solo == "pequenas": nombres = [n for n in nombres if es_pequena(n)]
    if a.solo == "grandes": nombres = [n for n in nombres if not es_pequena(n)]
    out = a.out or os.path.join(BASE, "resultados", a.metodo)
    sol_dir, log_dir = os.path.join(out, "soluciones"), os.path.join(out, "logs")
    os.makedirs(sol_dir, exist_ok=True); os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(out, "corridas.csv")

    filas = []
    if a.reanudar and os.path.exists(path):
        filas = list(csv.DictReader(open(path)))
    hechas = {(f["instancia"], int(f["semilla"])) for f in filas}
    nuevo = not (a.reanudar and os.path.exists(path))
    fh = open(path, "w" if nuevo else "a", newline="")
    w = csv.DictWriter(fh, fieldnames=CAMPOS)
    if nuevo: w.writeheader()
    for nombre in nombres:
        tiempo = a.t_pequenas if es_pequena(nombre) else a.t_grandes
        for s in a.semillas:
            if (nombre, s) in hechas:
                continue
            f = correr(a, nombre, s, tiempo, sol_dir, log_dir)
            w.writerow(f); fh.flush(); filas.append(f)
            print(f"{nombre} s={s} factible={f['factible']} K={f['K']} TC={f['costo_TC']} "
                  f"t={f['tiempo_pared']}s {f['errores'][:120]}", flush=True)
    fh.close()
    filas = [f for f in filas if f["instancia"] in nombres]
    if filas:
        resumir(filas, os.path.join(out, "resumen.csv"), os.path.join(out, "resumen.md"), a.metodo)
        print("resumen en", os.path.join(out, "resumen.md"))


if __name__ == "__main__":
    main()
