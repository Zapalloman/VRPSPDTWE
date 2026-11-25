"""Resúmenes de segmento concatenables para EVRP-TW-SPD con consumo según la carga.

Para una secuencia de nodos sigma (clientes y estaciones), el resumen guarda:
  - distancia d y número de clientes;
  - carga (estilo Vidal/HMA): U = sum u (entregas), Dl = sum (v - u) (variación neta),
    H = max_k Dl_k (máximo prefijo de la variación tras atender cada nodo, >= 0 se toma 0
    para el arco de llegada);
  - energía afín en la carga de entrada L (carga al LLEGAR al primer nodo):
        E(L) = h * [ (1 - beta*rho) * d + beta/C * (W + L * d) ],   W = sum_k d_k * Dl_k
    (Dl_k = variación neta acumulada antes del arco k, dentro del segmento);
  - ventanas de tiempo (Vidal et al. 2013): duración D, TE, TL y bandera de factibilidad
    (sin "time warp": un segmento infactible se marca y no se concatena);
  - si contiene estaciones: el resumen de la "pierna" de cabeza (hasta la 1.ª estación),
    la de cola (desde la última estación) y la lista de piernas intermedias. Las piernas
    son O(1) cada una; la evaluación de la recarga es O(m) con m = número de estaciones.

Evaluación de la recarga (greedy exacto, ver PROPUESTA.md): en cada estación se carga
lo obligatorio para llegar a la siguiente oportunidad de recarga más todo lo que quepa
"gratis" en la holgura TE - llegada de la pierna siguiente, sin superar lo que falta
por recorrer ni la batería Q.
"""
import math

INF = float("inf")
EPS = 1e-9


class Seg:
    __slots__ = ("first", "last", "ncus", "d", "U", "Dl", "H", "W",
                 "D", "TE", "TL", "ok",
                 # estructura de estaciones: piernas (lista de Seg sin estaciones interiores)
                 "legs")

    def copy(self):
        s = Seg.__new__(Seg)
        for k in Seg.__slots__:
            setattr(s, k, getattr(self, k))
        return s


class Model:
    def __init__(self, I, beta=0.2, rho=0.0):
        self.I = I
        self.beta, self.rho = beta, rho
        self.C, self.Q, self.h, self.g = I.C, I.Q, I.h, I.g
        self.k0 = I.h * (1.0 - beta * rho)
        self.k1 = I.h * beta / I.C
        self.dist, self.tm = I.dist, I.tm
        self._node = {}

    # ---------- energía ----------
    def energy(self, s, L):
        """Energía de los arcos internos de s con carga de llegada L (sin estaciones)."""
        return self.k0 * s.d + self.k1 * (s.W + L * s.d)

    # ---------- nodo ----------
    def node(self, i):
        c = self._node.get(i)
        if c is not None:
            return c
        I = self.I
        s = Seg.__new__(Seg)
        s.first = s.last = i
        t = I.typ[i]
        s.ncus = 1 if t == "c" else 0
        s.d = 0.0
        s.U = I.dlv[i] if t == "c" else 0.0
        s.Dl = (I.pck[i] - I.dlv[i]) if t == "c" else 0.0
        s.H = max(0.0, s.Dl)
        s.W = 0.0
        if t == "c":
            s.D, s.TE, s.TL = I.s[i], I.e[i], I.l[i]
        elif t == "d":
            s.D, s.TE, s.TL = 0.0, I.e[0], I.l[0]
        else:  # estación: sin ventana, el tiempo de carga se agrega en la evaluación
            s.D, s.TE, s.TL = 0.0, 0.0, INF
        s.ok = True
        s.legs = [s] if t == "f" else None  # una estación sola: dos piernas vacías
        if t == "f":
            s.legs = ("F",)  # marcador: segmento que es solo una estación
        self._node[i] = s
        return s

    # ---------- concatenación sin estaciones (O(1)) ----------
    def _cat_plain(self, a, b):
        x, y = a.last, b.first
        dxy, txy = self.dist[x, y], self.tm[x, y]
        s = Seg.__new__(Seg)
        s.first, s.last = a.first, b.last
        s.ncus = a.ncus + b.ncus
        s.d = a.d + dxy + b.d
        s.U = a.U + b.U
        s.Dl = a.Dl + b.Dl
        s.H = max(a.H, a.Dl + b.H)
        # W: los arcos de b y el arco (x,y) ven la variación de a desplazada
        s.W = a.W + a.Dl * dxy + b.W + a.Dl * b.d
        # Vidal (sin time warp)
        delta = a.D + txy - 0.0
        wt = max(b.TE - delta - a.TL, 0.0)
        s.ok = a.ok and b.ok and (a.TE + delta <= b.TL + 1e-9)
        s.D = a.D + b.D + txy + wt
        s.TE = max(b.TE - delta, a.TE) - wt
        s.TL = min(b.TL - delta, a.TL)
        s.legs = None
        return s

    # ---------- concatenación general ----------
    def cat(self, a, b):
        """a ⊕ b. Si alguno contiene estaciones, se guarda la lista de piernas."""
        if a.legs is None and b.legs is None:
            return self._cat_plain(a, b)
        # representar cada operando como (cabeza, [intermedias], cola) donde la cabeza y la
        # cola son segmentos sin estaciones que terminan/empiezan EN la estación.
        ha, ma, ta = self._parts(a)
        hb, mb, tb = self._parts(b)
        s = Seg.__new__(Seg)
        s.first, s.last = a.first, b.last
        s.ncus = a.ncus + b.ncus
        s.d = a.d + self.dist[a.last, b.first] + b.d
        s.U = a.U + b.U
        s.Dl = a.Dl + b.Dl
        s.H = max(a.H, a.Dl + b.H)
        s.W = a.W + a.Dl * self.dist[a.last, b.first] + b.W + a.Dl * b.d  # no se usa con estaciones
        s.D = s.TE = s.TL = None
        s.ok = a.ok and b.ok
        if ta is None:   # a sin estaciones: a se une a la cabeza de b
            head = self._cat_plain(a, hb)
            s.legs = (head, mb, tb)
        elif tb is None:  # b sin estaciones
            tail = self._cat_plain(ta, b)
            s.legs = (ha, ma, tail)
        else:
            mid = self._cat_plain(ta, hb)
            s.legs = (ha, ma + [mid] + mb, tb)
        return s

    def _parts(self, s):
        if s.legs is None:
            return s, [], None
        if s.legs == ("F",):
            n = self.node(s.first)
            return n, [], n
        return s.legs[0], s.legs[1], s.legs[2]

    def seq(self, nodes):
        s = self.node(nodes[0])
        for i in nodes[1:]:
            s = self.cat(s, self.node(i))
        return s

    # ---------- evaluación de una ruta completa (depósito ... depósito) ----------
    def eval_route(self, s):
        """Devuelve (factible, distancia). s es el resumen de la ruta completa."""
        C, Q, g = self.C, self.Q, self.g
        L0 = s.U  # sale con todas sus entregas
        if L0 > C + 1e-9 or L0 + s.H > C + 1e-9:
            return False, s.d
        if not s.ok:
            return False, s.d
        if s.legs is None:
            # sin estaciones: ventanas (Vidal) y energía afín, O(1)
            return (s.TE <= s.TL + 1e-9 and self.energy(s, L0) <= Q + 1e-9), s.d
        head, mids, tail = self._parts(s)
        legs = [head] + mids + [tail]
        # energías y cargas de entrada de cada pierna, O(m)
        E = []
        L = L0
        for lg in legs:
            E.append(self.energy(lg, L))
            L += lg.Dl
        if E[0] > Q + 1e-9:
            return False, s.d
        # tiempo: la cabeza empieza en el depósito
        if not head.ok or head.TE > head.TL + 1e-9:
            return False, s.d
        t = head.TE + head.D  # llegada a la 1.ª estación
        b = Q - E[0]
        rem = sum(E[1:])
        for k in range(1, len(legs)):
            lg = legs[k]
            if not lg.ok or E[k] > Q + 1e-9:
                return False, s.d
            need = max(0.0, E[k] - b)
            free = max(0.0, (lg.TE - t) / g) if g > 0 else INF
            q = max(need, min(free, rem - b, Q - b))
            t += g * q
            if t > lg.TL + 1e-7:
                return False, s.d
            t = max(t, lg.TE) + lg.D
            b = b + q - E[k]
            rem -= E[k]
        return True, s.d
