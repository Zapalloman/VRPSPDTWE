"""Compara los veredictos de la implementación C++ (evaluación completa y por resúmenes)
con el juez oficial en rutas generadas por las mutaciones de prueba_resumen.py y por la
prueba de estrés (Q reducido). Uso: python3 prueba_cpp.py [n_por_instancia] [beta]"""
import sys, glob, os, random, subprocess, copy, tempfile
sys.path.insert(0, "/home/user/oe3/common"); sys.path.insert(0, "/home/user/oe3/afin")
from evrp import read_instance, read_solution, eval_route
from prueba_resumen import mutate
H = "/home/user/oe3/common/hma"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
BETA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
tot = ag_f = ag_c = fe = 0
for f in sorted(glob.glob(f"{H}/data/akb_instances/*.txt")):
    name = os.path.basename(f)[:-4]
    sol = glob.glob(f"{H}/solution/akb/{name}_timelimit*")
    if not sol: continue
    I = read_instance(f); routes = [[x[0] for x in r] for r in read_solution(sol[0])[0]]
    rng = random.Random(name)
    cands = routes + [mutate(I, routes, rng) for _ in range(N)]
    tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt")
    for r in cands: tmp.write(" ".join(map(str, r)) + "\n")
    tmp.close()
    out = subprocess.run(["/home/user/oe3/afin/cpp/check_routes", f, tmp.name, str(BETA)],
                         capture_output=True, text=True).stdout.split("\n")
    os.unlink(tmp.name)
    for r, o in zip(cands, out):
        a, c = map(int, o.split())
        j = eval_route(I, r, BETA, 0.0)["feasible"]
        tot += 1; fe += j; ag_f += (a == j); ag_c += (c == j)
print(f"beta={BETA} rutas={tot} factibles juez={fe}  C++ completa coincide={ag_f}  C++ resúmenes coincide={ag_c}")
