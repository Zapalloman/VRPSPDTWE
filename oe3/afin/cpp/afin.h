// Resúmenes de segmento concatenables (afín en la carga) para EVRP-TW-SPD con consumo
// según la carga: e_ij(L) = h d_ij (1 + beta (L/C - rho)).
// Ver /home/user/oe3/afin/PROPUESTA.md para la derivación.
#pragma once
#include <vector>
#include <cmath>
#include <algorithm>
#include <string>

namespace afin {

const double INF = 1e30;
const int MAXLEG = 8;  // máximo de piernas (estaciones + 1) por segmento

struct Inst {
    int n;                       // nodos
    std::vector<int> typ;        // 0 depósito, 1 cliente, 2 estación
    std::vector<double> u, v, e, l, s;
    std::vector<double> dist, tm;  // n*n
    double C, Q, h, g, mu1, mu2;
    double beta = 0.2, rho = 0.0;
    double k0, k1;               // h(1-beta rho), h beta / C
    inline double d(int a, int b) const { return dist[a * n + b]; }
    inline double t(int a, int b) const { return tm[a * n + b]; }
    void finalize() { k0 = h * (1 - beta * rho); k1 = h * beta / C; }
};

bool read_instance(const std::string &path, Inst &I);
std::vector<std::vector<int>> read_solution(const std::string &path);

// Resumen sin estaciones interiores (una "pierna"): O(1) por concatenación.
struct Plain {
    int first, last;
    int ncus;
    double d;      // distancia interna
    double U;      // suma de entregas
    double Dl;     // variación neta de carga (v - u)
    double H;      // máximo prefijo de variación (>= 0)
    double W;      // sum_k d_k * Dl_k (para la energía afín)
    double D, TE, TL;  // Vidal: duración, inicio más temprano/tardío sin espera extra
    bool ok;
};

inline double energy(const Inst &I, const Plain &p, double L) {
    return I.k0 * p.d + I.k1 * (p.W + L * p.d);
}

inline void node_plain(const Inst &I, int i, Plain &p) {
    p.first = p.last = i; p.d = 0; p.W = 0; p.ok = true;
    if (I.typ[i] == 1) {
        p.ncus = 1; p.U = I.u[i]; p.Dl = I.v[i] - I.u[i]; p.H = std::max(0.0, p.Dl);
        p.D = I.s[i]; p.TE = I.e[i]; p.TL = I.l[i];
    } else {
        p.ncus = 0; p.U = 0; p.Dl = 0; p.H = 0;
        if (I.typ[i] == 0) { p.D = 0; p.TE = I.e[0]; p.TL = I.l[0]; }
        else { p.D = 0; p.TE = 0; p.TL = INF; }
    }
}

inline void cat_plain(const Inst &I, const Plain &a, const Plain &b, Plain &r) {
    const int x = a.last, y = b.first;
    const double dxy = I.d(x, y), txy = I.t(x, y);
    const double delta = a.D + txy;
    const double wt = std::max(b.TE - delta - a.TL, 0.0);
    r.ok = a.ok && b.ok && (a.TE + delta <= b.TL + 1e-9);
    r.first = a.first; r.last = b.last;
    r.ncus = a.ncus + b.ncus;
    r.W = a.W + b.W + a.Dl * (dxy + b.d);
    r.d = a.d + dxy + b.d;
    r.U = a.U + b.U;
    r.H = std::max(a.H, a.Dl + b.H);
    r.Dl = a.Dl + b.Dl;
    r.D = a.D + b.D + txy + wt;
    r.TE = std::max(b.TE - delta, a.TE) - wt;
    r.TL = std::min(b.TL - delta, a.TL);
}

// Resumen general: piernas separadas por estaciones. m = nleg-1 estaciones.
// leg[0] termina en la 1.ª estación, leg[k] va de la estación k a la k+1, leg[nleg-1]
// empieza en la última estación. Si nleg == 1 el segmento no tiene estaciones.
struct Seg {
    int nleg;
    Plain leg[MAXLEG];
    // agregados (para costo y carga)
    inline double dist(const Inst &I) const {
        double r = 0; for (int k = 0; k < nleg; k++) r += leg[k].d; return r;
    }
};

inline void node_seg(const Inst &I, int i, Seg &s) {
    if (I.typ[i] == 2) { s.nleg = 2; node_plain(I, i, s.leg[0]); s.leg[1] = s.leg[0]; }
    else { s.nleg = 1; node_plain(I, i, s.leg[0]); }
}

// r = a ⊕ b  (r no puede ser alias de b)
inline bool cat(const Inst &I, const Seg &a, const Seg &b, Seg &r) {
    if (a.nleg + b.nleg - 1 > MAXLEG) return false;
    if (&r != &a) { for (int k = 0; k < a.nleg - 1; k++) r.leg[k] = a.leg[k]; }
    Plain mid;
    cat_plain(I, a.leg[a.nleg - 1], b.leg[0], mid);
    int na = a.nleg;
    r.leg[na - 1] = mid;
    for (int k = 1; k < b.nleg; k++) r.leg[na - 1 + k] = b.leg[k];
    r.nleg = na + b.nleg - 1;
    return true;
}

// Evaluación exacta de una ruta completa (depósito ... depósito) a partir de su resumen.
// O(m). Devuelve factible y escribe la distancia.
inline bool eval_route(const Inst &I, const Seg &s, double &dist) {
    double U = 0, H = 0, Dl = 0; dist = 0;
    for (int k = 0; k < s.nleg; k++) {
        const Plain &p = s.leg[k];
        H = std::max(H, Dl + p.H); Dl += p.Dl; U += p.U; dist += p.d;
    }
    const double L0 = U;
    if (L0 + H > I.C + 1e-9) return false;
    const Plain &h0 = s.leg[0];
    if (!h0.ok) return false;
    if (s.nleg == 1)
        return energy(I, h0, L0) <= I.Q + 1e-9;
    double E[MAXLEG]; double L = L0, rem = 0;
    for (int k = 0; k < s.nleg; k++) { E[k] = energy(I, s.leg[k], L); L += s.leg[k].Dl; if (k) rem += E[k]; }
    if (E[0] > I.Q + 1e-9) return false;
    double t = h0.TE + h0.D, b = I.Q - E[0];
    for (int k = 1; k < s.nleg; k++) {
        const Plain &p = s.leg[k];
        if (!p.ok || E[k] > I.Q + 1e-9) return false;
        double need = std::max(0.0, E[k] - b);
        double fr = std::max(0.0, (p.TE - t) / I.g);
        double q = std::max(need, std::min(fr, std::min(rem - b, I.Q - b)));
        t += I.g * q;
        if (t > p.TL + 1e-7) return false;
        t = std::max(t, p.TE) + p.D;
        b += q - E[k]; rem -= E[k];
    }
    return true;
}

// Evaluación completa O(n) "estilo HMA" (simulación hacia adelante; para cada estación
// se recorre la pierna siguiente para calcular la carga obligatoria y la holgura).
bool eval_full(const Inst &I, const int *nl, int len, double &dist);

}  // namespace afin
