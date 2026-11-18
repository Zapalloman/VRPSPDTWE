"""Prueba de concepto (OE2): re-evaluación de soluciones de HMA con consumo
dependiente de la carga y reparación mínima de las rutas que dejan de ser factibles.

e_ij(L) = h * d_ij * (1 + beta * (L / C - rho))
  rho = 0   -> la tasa publicada h corresponde al vehículo vacío (calibración en vacío)
  rho = 0.5 -> h corresponde a media carga (calibración neutra)
"""
import glob, os, sys, json
from evrp import *

H = sys.argv[1]
BETAS = [0.0, 0.1, 0.2, 0.3, 0.4]
RHOS = [0.0, 0.5]


def energy_screen(I, nodes, beta, rho):
    """Condición necesaria barata: cada tramo entre oportunidades de recarga cabe en la batería."""
    load = sum(I.dlv[i] for i in nodes if I.typ[i] == "c"); seg = 0.0
    for k in range(len(nodes) - 1):
        i = nodes[k]
        if k > 0 and I.typ[i] == "c":
            load = load - I.dlv[i] + I.pck[i]
        if k > 0 and I.typ[i] == "f":
            seg = 0.0
        seg += energy(I, i, nodes[k + 1], load, beta, rho)
        if seg > I.Q + 1e-9:
            return False
    return True


def route_ok(I, nodes, beta, rho):
    if not energy_screen(I, nodes, beta, rho):
        return False, None
    o = eval_route(I, nodes, beta, rho)
    return o["feasible"], o


def repair(I, nodes, beta, rho):
    """Reparaciones mínimas que no cambian la asignación de clientes.
    Devuelve (método, nodos, distancia extra) o None."""
    rev = nodes[::-1]
    ok, _ = route_ok(I, rev, beta, rho)
    if ok:
        return ("invertir", rev, 0.0)
    best = None
    stations = I.stations
    for base, tag in ((nodes, "estacion"), (rev, "invertir+estacion")):
        for k in range(len(base) - 1):
            a, b = base[k], base[k + 1]
            for f in stations:
                if f in (a, b):
                    continue
                extra = I.dist[a, f] + I.dist[f, b] - I.dist[a, b]
                if best is not None and extra >= best[2] - 1e-9:
                    continue
                cand = base[:k + 1] + [f] + base[k + 1:]
                if route_ok(I, cand, beta, rho)[0]:
                    best = (tag, cand, extra)
    return best


def analyse(I, routes):
    out = {}
    base_e = None
    for rho in RHOS:
        for beta in BETAS:
            if beta == 0.0 and rho != RHOS[0]:
                out[f"b{beta}_r{rho}"] = out[f"b0.0_r{RHOS[0]}"]; continue
            R = []
            for r in routes:
                nodes = [x[0] for x in r]
                o = eval_route(I, nodes, beta, rho); ok = o["feasible"]
                rec = dict(feasible=ok, energy=o["energy"], charge_t=o["charge_t"], dist=o["dist"],
                           n_cust=sum(I.typ[i] == "c" for i in nodes))
                # efecto de la secuencia: invertir la ruta (misma distancia) sin considerar ventanas
                rev = nodes[::-1]
                orev = eval_route(I, rev, beta, rho)
                rec["energy_rev"] = orev["energy"]; rec["rev_feasible"] = orev["feasible"]
                if not ok:
                    rp = repair(I, nodes, beta, rho)
                    rec["repair"] = None if rp is None else rp[0]
                    rec["repair_extra"] = None if rp is None else rp[2]
                R.append(rec)
            out[f"b{beta}_r{rho}"] = R
    return out


def one(f):
    base = os.path.basename(f).split('_timelimit')[0]
    I = read_instance(H + '/data/akb_instances/' + base + '.txt')
    R, T = read_solution(f)
    d = dict(n=len(I.customers), K=len(R), cost=T, Q=I.Q, C=I.C, analysis=analyse(I, R))
    a = d['analysis']
    print(base, len(R), [sum(not x['feasible'] for x in a[f'b{b}_r0.0']) for b in BETAS],
          [sum(not x['feasible'] for x in a[f'b{b}_r0.5']) for b in BETAS], flush=True)
    return base, d


def main():
    from multiprocessing import Pool
    which = sys.argv[2]  # 'publicadas' o carpeta con soluciones locales
    files = sorted(glob.glob(H + '/solution/akb/*.txt')) if which == 'publicadas' else sorted(glob.glob(which + '/*_subproblem=1.txt'))
    files.sort(key=lambda f: '_21' in f)  # pequeñas primero
    with Pool(4) as p:
        res = dict(p.map(one, files, chunksize=1))
    json.dump(res, open(sys.argv[3], 'w'), default=float)


if __name__ == '__main__':
    main()
