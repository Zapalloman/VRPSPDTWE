"""Comprobador independiente y evaluador de rutas para EVRP-TW-SPD (VRPSPDTW-E).

Escrito desde la definición del problema (Zheng et al., 2025; Akbay et al., 2022),
sin reutilizar código de HMA. Soporta consumo constante (modelo original) y
consumo dependiente de la carga:

    e_ij(L) = h * d_ij * (1 + beta * (L / C - rho))

donde L es la carga a bordo en el arco (i, j), C la capacidad, beta la
sensibilidad a la carga y rho la carga de referencia a la que el consumo
coincide con h. beta = 0 recupera el modelo original.
"""
import re
import numpy as np
from scipy.optimize import linprog
from dataclasses import dataclass, field

EPS = 1e-6


@dataclass
class Instance:
    name: str
    mu1: float
    mu2: float
    C: float
    Q: float
    h: float
    g: float
    typ: dict = field(default_factory=dict)
    dlv: dict = field(default_factory=dict)
    pck: dict = field(default_factory=dict)
    e: dict = field(default_factory=dict)
    l: dict = field(default_factory=dict)
    s: dict = field(default_factory=dict)
    dist: dict = field(default_factory=dict)
    tm: dict = field(default_factory=dict)

    @property
    def customers(self):
        return [i for i, t in self.typ.items() if t == "c"]

    @property
    def stations(self):
        return [i for i, t in self.typ.items() if t == "f"]


def read_instance(path):
    hdr, nodes, edges, sec = {}, [], [], None
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        if line.startswith("NODE_SECTION"):
            sec = "n"; continue
        if line.startswith("DISTANCETIME_SECTION"):
            sec = "d"; continue
        if line.startswith("DEPOT_SECTION"):
            break
        if line.startswith("ID,"):
            continue
        if sec is None and ":" in line:
            k, v = line.split(":", 1); hdr[k.strip()] = v.strip()
        elif sec == "n":
            nodes.append(line.split(","))
        elif sec == "d":
            edges.append(line.split(","))
    I = Instance(hdr["NAME"], float(hdr["DISPATCHINGCOST"]), float(hdr["UNITCOST"]),
                 float(hdr["CAPACITY"]), float(hdr["ELECTRIC_POWER"]),
                 float(hdr["CONSUMPTION_RATE"]), float(hdr["RECHARGING_RATE"]))
    for r in nodes:
        i = int(r[0]); I.typ[i] = r[1]
        I.dlv[i], I.pck[i] = float(r[4]), float(r[5])
        I.e[i], I.l[i], I.s[i] = float(r[6]), float(r[7]), float(r[8])
    for r in edges:
        a, b = int(r[1]), int(r[2])
        I.dist[a, b] = float(r[3]); I.tm[a, b] = float(r[4])
    for i in I.typ:
        I.dist.setdefault((i, i), 0.0); I.tm.setdefault((i, i), 0.0)
    return I


TOKEN = re.compile(r"(\d+)(?:\(([-\d.]+),\s*([-\d.]+)\))?")


def read_solution(path):
    """Devuelve (rutas, costo_reportado). Cada ruta: lista de (nodo, y, Y) con y/Y None si no se informan."""
    routes, total = [], None
    for line in open(path):
        if line.startswith("route"):
            seq = line.split("nodes:", 1)[1]
            routes.append([(int(m.group(1)),
                            float(m.group(2)) if m.group(2) else None,
                            float(m.group(3)) if m.group(3) else None)
                           for m in TOKEN.finditer(seq)])
        elif line.startswith("Total cost"):
            total = float(line.split(":")[1])
    return routes, total


def energy(I, a, b, load, beta=0.0, rho=0.0):
    return I.h * I.dist[a, b] * (1.0 + beta * (load / I.C - rho))


def eval_route(I, nodes, beta=0.0, rho=0.0, charges=None):
    """Evalúa una ruta fija (lista de ids, empieza y termina en el depósito).

    charges=None  -> decide la recarga resolviendo un programa lineal exacto
                     (plan_recarga): para una secuencia fija, cuánto cargar en
                     cada estación de modo que se cumplan batería y ventanas.
    charges=dict  -> {posición: energía cargada} informada por la solución.
    Devuelve dict con distancia, energía, tiempo de recarga, violaciones, etc.
    """
    v = {"load": 0.0, "tw": 0.0, "bat": 0.0, "batmax": 0.0, "struct": []}
    if nodes[0] != 0 or nodes[-1] != 0:
        v["struct"].append("la ruta no empieza/termina en el depósito")
    n = len(nodes)
    load = sum(I.dlv[i] for i in nodes if I.typ[i] == "c")
    if load > I.C + EPS:
        v["load"] = max(v["load"], load - I.C)
    loads = []  # carga en cada arco (k -> k+1)
    for k in range(n - 1):
        i = nodes[k]
        if k > 0 and I.typ[i] == "c":
            load = load - I.dlv[i] + I.pck[i]
            if load > I.C + EPS:
                v["load"] = max(v["load"], load - I.C)
        loads.append(load)
    arcE = [energy(I, nodes[k], nodes[k + 1], loads[k], beta, rho) for k in range(n - 1)]
    planned = charges is None
    if charges is None:
        charges = plan_recarga(I, nodes, arcE)
        if charges is None:  # no existe plan de recarga factible para la secuencia
            charges = plan_recarga(I, nodes, arcE, relax=True)
    t, b = I.e[0], I.Q
    dist = tot_e = chg_e = chg_t = wait = 0.0
    min_b = b
    for k in range(n - 1):
        i = nodes[k]
        if k > 0:
            if I.typ[i] == "c":
                start = max(t, I.e[i]); wait += start - t
                if start > I.l[i] + EPS:
                    v["tw"] += start - I.l[i]
                t = start + I.s[i]
            elif I.typ[i] == "f":
                q = charges.get(k, 0.0)
                b += q; chg_e += q; chg_t += I.g * q; t += I.g * q
                if b > I.Q + 1e-2:
                    v["batmax"] = max(v["batmax"], b - I.Q)
        t += I.tm[i, nodes[k + 1]]
        dist += I.dist[i, nodes[k + 1]]
        b -= arcE[k]; tot_e += arcE[k]
        min_b = min(min_b, b)
    if t > I.l[0] + EPS:
        v["tw"] += t - I.l[0]
    tol = 1e-5 if planned else 1e-2  # la solución informa la batería con 2 decimales
    if min_b < -tol:
        v["bat"] = -min_b
    feasible = not v["struct"] and v["load"] <= EPS and v["tw"] <= EPS and v["bat"] <= tol and v["batmax"] <= 1e-2
    return {"feasible": bool(feasible), "viol": v, "dist": dist, "energy": tot_e, "charge_e": chg_e,
            "charge_t": chg_t, "wait": wait, "end_t": t, "min_battery": min_b,
            "max_load": max(loads) if loads else 0.0, "load_profile": loads}


def plan_recarga(I, nodes, arcE, relax=False):
    """Programa lineal del plan de recarga para una secuencia fija.

    Variables: q_k (energía cargada en la posición k, solo estaciones) y
    A_k (inicio de atención en la posición k). Restricciones: batería en
    [0, Q] en todo punto, inicio >= llegada, ventanas [e, l] en clientes y
    regreso al depósito antes de l_0. Minimiza la hora de regreso más un
    término pequeño de energía cargada. Con relax=True permite atraso
    (penalizado) para informar la magnitud de la violación.
    """
    n = len(nodes)
    st = [k for k in range(1, n - 1) if I.typ[nodes[k]] == "f"]
    nq, nA = len(st), n
    nv = nq + nA + (n if relax else 0)
    qi = {k: j for j, k in enumerate(st)}
    A = lambda k: nq + k
    Z = lambda k: nq + nA + k
    Aub, bub = [], []
    # batería al llegar a la posición m >= 0  ->  Q + sum_{k<m} q_k - sum_{k<m} E_k >= 0
    cum = 0.0
    for m in range(1, n):
        cum += arcE[m - 1]
        row = np.zeros(nv)
        for k in st:
            if k < m: row[qi[k]] = -1.0
        Aub.append(row); bub.append(I.Q - cum)
        if m < n - 1 and I.typ[nodes[m]] == "f":  # batería tras cargar <= Q
            row = np.zeros(nv)
            for k in st:
                if k <= m: row[qi[k]] = 1.0
            Aub.append(row); bub.append(cum)
    for k in range(n - 1):
        # A_{k+1} >= A_k + s_k + g q_k + t
        row = np.zeros(nv); row[A(k)] = 1.0; row[A(k + 1)] = -1.0
        if k in qi: row[qi[k]] = I.g
        Aub.append(row); bub.append(-(I.s[nodes[k]] if k > 0 else 0.0) - I.tm[nodes[k], nodes[k + 1]])
    bounds = [(0, I.Q)] * nq
    for k in range(n):
        i = nodes[k]
        lo = I.e[i] if (I.typ[i] == "c" or k == 0) else 0.0
        hi = I.l[i] if (I.typ[i] == "c" or k == n - 1) else None
        if k == 0: hi = I.e[0]
        if relax and hi is not None and k > 0:
            row = np.zeros(nv); row[A(k)] = 1.0; row[Z(k)] = -1.0
            Aub.append(row); bub.append(hi); hi = None
        bounds.append((lo, hi))
    if relax: bounds += [(0, None)] * n
    c = np.zeros(nv); c[A(n - 1)] = 1.0; c[:nq] = 1e-3
    if relax: c[nq + nA:] = 1e4
    r = linprog(c, A_ub=np.array(Aub), b_ub=np.array(bub), bounds=bounds, method="highs")
    if r.status != 0:
        return None if not relax else {k: 0.0 for k in st}
    return {k: max(0.0, r.x[qi[k]]) for k in st}


def reported_charges(I, route):
    ch = {}
    for k, (i, y, Y) in enumerate(route):
        if 0 < k < len(route) - 1 and I.typ[i] == "f" and y is not None:
            ch[k] = (Y - y) * I.h  # el archivo informa la batería en unidades de distancia (y/h)
    return ch


def check_solution(I, routes, reported_total=None, beta=0.0, rho=0.0, use_reported=True):
    """Comprobación independiente completa de una solución."""
    errs = []
    seen = {}
    for r in routes:
        for i, *_ in r[1:-1]:
            if I.typ.get(i) == "c":
                seen[i] = seen.get(i, 0) + 1
            elif I.typ.get(i) == "d":
                errs.append("depósito en medio de una ruta")
            elif i not in I.typ:
                errs.append(f"nodo {i} inexistente")
    missing = [c for c in I.customers if seen.get(c, 0) == 0]
    dup = [c for c, k in seen.items() if k > 1]
    if missing: errs.append(f"clientes sin atender: {missing}")
    if dup: errs.append(f"clientes atendidos más de una vez: {dup}")
    res = []
    for ridx, r in enumerate(routes):
        nodes = [x[0] for x in r]
        ch = reported_charges(I, r) if use_reported else None
        out = eval_route(I, nodes, beta, rho, ch)
        res.append(out)
        if not out["feasible"]:
            errs.append(f"ruta {ridx}: {out['viol']}")
    K = len(routes)
    D = sum(o["dist"] for o in res)
    cost = I.mu1 * K + I.mu2 * D
    if reported_total is not None and abs(cost - reported_total) > 0.01:
        errs.append(f"costo recalculado {cost:.2f} != informado {reported_total:.2f}")
    return {"ok": not errs, "errors": errs, "K": K, "dist": D, "cost": cost,
            "energy": sum(o["energy"] for o in res),
            "charge_t": sum(o["charge_t"] for o in res), "routes": res}
