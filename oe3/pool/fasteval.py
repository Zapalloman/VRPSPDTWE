"""Evaluación rápida de rutas con consumo según la carga (β=0,2, ρ=0).

Filtro en tres pasos para una secuencia fija:
  1. condiciones necesarias baratas (capacidad, cada tramo entre recargas cabe
     en la batería, ventanas con tiempo de recarga cero);
  2. plan de recarga "lo más tarde posible" (cargar justo lo necesario para
     llegar a la próxima oportunidad de recarga): si cumple todo, la ruta es
     factible (condición suficiente);
  3. si 2 falla pero 1 pasa, se llama al programa lineal exacto de
     common/evrp.py (eval_route), que es el juez oficial.
Toda solución final se vuelve a comprobar con check_solution.
"""
import sys
sys.path.insert(0, '/home/user/oe3/common')
import numpy as np
from evrp import read_instance, eval_route, check_solution

BETA, RHO = 0.2, 0.0


class Fast:
    def __init__(self, path, beta=BETA, rho=RHO):
        I = read_instance(path)
        self.I = I
        self.beta, self.rho = beta, rho
        n = max(I.typ) + 1
        self.n = n
        self.D = np.zeros((n, n)); self.T = np.zeros((n, n))
        for (a, b), v in I.dist.items():
            self.D[a, b] = v
        for (a, b), v in I.tm.items():
            self.T[a, b] = v
        self.Dl = self.D.tolist(); self.Tl = self.T.tolist()
        self.typ = [I.typ[i] for i in range(n)]
        self.u = [I.dlv[i] for i in range(n)]
        self.v = [I.pck[i] for i in range(n)]
        self.e = [I.e[i] for i in range(n)]
        self.l = [I.l[i] for i in range(n)]
        self.s = [I.s[i] for i in range(n)]
        self.cust = I.customers
        self.stations = I.stations
        self.C, self.Q, self.h, self.g = I.C, I.Q, I.h, I.g
        self.cache = {}
        self.n_eval = 0; self.n_lp = 0

    def arc_energy(self, nodes):
        """Devuelve (lista de energías por arco, ok capacidad)."""
        u, v, C = self.u, self.v, self.C
        load = 0.0
        for i in nodes:
            if self.typ[i] == 'c':
                load += u[i]
        if load > C + 1e-6:
            return None
        k1 = self.h * self.beta / C
        k0 = self.h * (1 - self.beta * self.rho)
        Dl = self.Dl
        E = []
        prev = nodes[0]
        for k in range(1, len(nodes)):
            i = nodes[k]
            E.append(Dl[prev][i] * (k0 + k1 * load))
            if self.typ[i] == 'c':
                load += v[i] - u[i]
                if load > C + 1e-6:
                    return None
            prev = i
        return E

    def feasible(self, nodes):
        """nodes: tupla que empieza y termina en 0. Devuelve distancia o None."""
        key = tuple(nodes)
        r = self.cache.get(key, 0)
        if r != 0:
            return r
        self.n_eval += 1
        res = self._feasible(key)
        self.cache[key] = res
        return res

    def _feasible(self, nodes):
        E = self.arc_energy(nodes)
        if E is None:
            return None
        Q, typ = self.Q, self.typ
        n = len(nodes)
        # tramos entre oportunidades de recarga
        seg = 0.0
        need = [0.0] * n  # energía hasta la siguiente estación/depósito desde la posición k
        for k in range(n - 1):
            if k > 0 and typ[nodes[k]] == 'f':
                seg = 0.0
            seg += E[k]
            if seg > Q + 1e-9:
                return None
        acc = 0.0
        for k in range(n - 2, -1, -1):
            acc += E[k]
            need[k] = acc
            if k > 0 and typ[nodes[k]] == 'f':
                acc = 0.0
        # recorrido con recarga tardía y chequeo de ventanas con recarga cero
        Tl, e, l, s, g = self.Tl, self.e, self.l, self.s, self.g
        t = e[0]; t0 = e[0]; b = Q
        ok_late = True
        for k in range(n - 1):
            i = nodes[k]
            if k > 0:
                if typ[i] == 'c':
                    if t0 < e[i]: t0 = e[i]
                    if t0 > l[i] + 1e-6:
                        return None
                    t0 += s[i]
                    if ok_late:
                        if t < e[i]: t = e[i]
                        if t > l[i] + 1e-6:
                            ok_late = False
                        t += s[i]
                elif typ[i] == 'f':
                    q = need[k] - b
                    if q > 0:
                        b += q; t += g * q
            j = nodes[k + 1]
            t += Tl[i][j]; t0 += Tl[i][j]
            b -= E[k]
        if t0 > l[0] + 1e-6:
            return None
        dist = 0.0
        Dl = self.Dl
        for k in range(n - 1):
            dist += Dl[nodes[k]][nodes[k + 1]]
        if ok_late and t <= l[0] + 1e-6 and b >= -1e-7:
            return dist
        # caso dudoso: LP exacto
        if not any(typ[i] == 'f' for i in nodes[1:-1]):
            return None
        self.n_lp += 1
        o = eval_route(self.I, list(nodes), self.beta, self.rho)
        return o['dist'] if o['feasible'] else None

    def judge(self, routes):
        R = [[(i, None, None) for i in r] for r in routes]
        return check_solution(self.I, R, None, beta=self.beta, rho=self.rho, use_reported=False)

    def route_dist(self, nodes):
        Dl = self.Dl
        return sum(Dl[nodes[k]][nodes[k + 1]] for k in range(len(nodes) - 1))
