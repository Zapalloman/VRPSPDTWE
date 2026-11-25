"""Pruebas aleatorias del resumen concatenable contra el juez oficial (common/evrp.py).

Para cada instancia akb genera rutas (de las soluciones publicadas de HMA y mutaciones
suyas: intercambios, reubicaciones, inversiones, quitar/insertar estaciones, mezclar
rutas) y compara:
  (1) factibilidad del resumen (greedy O(m)) vs. eval_route (programa lineal exacto);
  (2) energía afín del resumen vs. energía arco a arco;
  (3) que el resumen no dependa del orden de concatenación (árbol aleatorio).
Uso: python3 prueba_resumen.py [n_rutas_por_instancia] [beta]
"""
import sys, glob, os, random, time
sys.path.insert(0, "/home/user/oe3/common")
from evrp import read_instance, read_solution, eval_route, energy
from resumen import Model

H = "/home/user/oe3/common/hma"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
BETA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
random.seed(12345)


def mutate(I, routes, rng):
    r = list(rng.choice(routes))
    inner = r[1:-1]
    st = I.stations
    op = rng.randrange(8)
    if op == 0 and len(inner) >= 2:
        i, j = rng.sample(range(len(inner)), 2); inner[i], inner[j] = inner[j], inner[i]
    elif op == 1 and len(inner) >= 2:
        i = rng.randrange(len(inner)); x = inner.pop(i); inner.insert(rng.randrange(len(inner) + 1), x)
    elif op == 2:
        inner = inner[::-1]
    elif op == 3:
        fs = [k for k, x in enumerate(inner) if I.typ[x] == "f"]
        if fs: inner.pop(rng.choice(fs))
    elif op == 4:
        inner.insert(rng.randrange(len(inner) + 1), rng.choice(st))
    elif op == 5:  # 2-opt* con otra ruta
        o = list(rng.choice(routes))[1:-1]
        a, b = rng.randrange(len(inner) + 1), rng.randrange(len(o) + 1)
        inner = inner[:a] + o[b:]
    elif op == 6:  # reubicar un cliente de otra ruta
        o = [x for x in rng.choice(routes)[1:-1] if I.typ[x] == "c" and x not in inner]
        if o: inner.insert(rng.randrange(len(inner) + 1), rng.choice(o))
    else:
        pass
    # evitar estaciones repetidas consecutivas idénticas (el juez las admite, se dejan)
    return [0] + inner + [0]


def tree_seq(M, nodes, rng):
    """Construye el resumen con un árbol de concatenación aleatorio."""
    if len(nodes) == 1:
        return M.node(nodes[0])
    k = rng.randrange(1, len(nodes))
    return M.cat(tree_seq(M, nodes[:k], rng), tree_seq(M, nodes[k:], rng))


def main():
    files = sorted(glob.glob(f"{H}/data/akb_instances/*.txt"))
    tot = agree = fe_j = fe_s = 0
    fp = fn = 0
    emax = 0.0
    tree_bad = 0
    t_lp = t_s = 0.0
    bad = []
    for f in files:
        name = os.path.basename(f)[:-4]
        sol = glob.glob(f"{H}/solution/akb/{name}_timelimit*")
        if not sol:
            continue
        I = read_instance(f)
        routes = [[x[0] for x in r] for r in read_solution(sol[0])[0]]
        M = Model(I, BETA, 0.0)
        rng = random.Random(hash(name) & 0xffff)
        cands = list(routes)
        for _ in range(N):
            cands.append(mutate(I, routes, rng))
        for nodes in cands:
            t0 = time.perf_counter()
            jr = eval_route(I, nodes, BETA, 0.0)
            t1 = time.perf_counter()
            s = M.seq(nodes)
            ok, d = M.eval_route(s)
            t2 = time.perf_counter()
            t_lp += t1 - t0; t_s += t2 - t1
            tot += 1
            fe_j += jr["feasible"]; fe_s += ok
            if ok == jr["feasible"]:
                agree += 1
            else:
                if ok: fp += 1
                else: fn += 1
                bad.append((name, nodes, jr["viol"], ok))
            # energía afín (sin estaciones, la energía total es independiente del plan)
            if s.legs is None and s.U <= I.C:
                emax = max(emax, abs(M.energy(s, s.U) - jr["energy"]))
            # independencia del árbol
            s2 = tree_seq(M, nodes, rng)
            ok2, _ = M.eval_route(s2)
            if ok2 != ok or abs(s2.d - s.d) > 1e-6:
                tree_bad += 1
    print(f"beta={BETA}  rutas={tot}  factibles juez={fe_j}  factibles resumen={fe_s}")
    print(f"coinciden={agree}  falsos positivos={fp}  falsos negativos={fn}")
    print(f"error máx. energía afín={emax:.2e}   árbol≠secuencial={tree_bad}")
    print(f"tiempo LP={t_lp:.1f}s  resumen(construcción O(n)+eval)={t_s:.2f}s")
    for b in bad[:10]:
        print("DISCREPANCIA", b)


if __name__ == "__main__":
    main()
