#include "afin.h"
#include <fstream>
#include <sstream>
#include <cstdio>
#include <cstdlib>

namespace afin {

static std::string trim(const std::string &s) {
    size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
    return a == std::string::npos ? "" : s.substr(a, b - a + 1);
}

bool read_instance(const std::string &path, Inst &I) {
    std::ifstream f(path);
    if (!f) return false;
    std::string line; int sec = 0;
    std::vector<std::vector<std::string>> nodes, edges;
    while (std::getline(f, line)) {
        line = trim(line);
        if (line.empty()) continue;
        if (line.rfind("NODE_SECTION", 0) == 0) { sec = 1; continue; }
        if (line.rfind("DISTANCETIME_SECTION", 0) == 0) { sec = 2; continue; }
        if (line.rfind("DEPOT_SECTION", 0) == 0) break;
        if (line.rfind("ID,", 0) == 0) continue;
        if (sec == 0) {
            size_t p = line.find(':'); if (p == std::string::npos) continue;
            std::string k = trim(line.substr(0, p)), v = trim(line.substr(p + 1));
            if (k == "DISPATCHINGCOST") I.mu1 = atof(v.c_str());
            else if (k == "UNITCOST") I.mu2 = atof(v.c_str());
            else if (k == "CAPACITY") I.C = atof(v.c_str());
            else if (k == "ELECTRIC_POWER") I.Q = atof(v.c_str());
            else if (k == "CONSUMPTION_RATE") I.h = atof(v.c_str());
            else if (k == "RECHARGING_RATE") I.g = atof(v.c_str());
        } else {
            std::vector<std::string> t; std::stringstream ss(line); std::string x;
            while (std::getline(ss, x, ',')) t.push_back(x);
            (sec == 1 ? nodes : edges).push_back(t);
        }
    }
    int n = 0;
    for (auto &r : nodes) n = std::max(n, atoi(r[0].c_str()) + 1);
    I.n = n; I.typ.assign(n, 0); I.u.assign(n, 0); I.v.assign(n, 0);
    I.e.assign(n, 0); I.l.assign(n, 0); I.s.assign(n, 0);
    I.dist.assign(n * n, 0); I.tm.assign(n * n, 0);
    for (auto &r : nodes) {
        int i = atoi(r[0].c_str());
        I.typ[i] = r[1] == "d" ? 0 : (r[1] == "c" ? 1 : 2);
        I.u[i] = atof(r[4].c_str()); I.v[i] = atof(r[5].c_str());
        I.e[i] = atof(r[6].c_str()); I.l[i] = atof(r[7].c_str()); I.s[i] = atof(r[8].c_str());
    }
    for (auto &r : edges) {
        int a = atoi(r[1].c_str()), b = atoi(r[2].c_str());
        I.dist[a * n + b] = atof(r[3].c_str()); I.tm[a * n + b] = atof(r[4].c_str());
    }
    I.finalize();
    return true;
}

std::vector<std::vector<int>> read_solution(const std::string &path) {
    std::vector<std::vector<int>> R;
    std::ifstream f(path); std::string line;
    while (std::getline(f, line)) {
        if (line.rfind("route", 0) != 0) continue;
        std::string seq = line.substr(line.find("nodes:") + 6);
        std::vector<int> r; size_t i = 0;
        while (i < seq.size()) {
            if (isdigit(seq[i])) {
                size_t j = i; while (j < seq.size() && isdigit(seq[j])) j++;
                r.push_back(atoi(seq.substr(i, j - i).c_str()));
                if (j < seq.size() && seq[j] == '(') { j = seq.find(')', j) + 1; }
                i = j;
            } else i++;
        }
        R.push_back(r);
    }
    return R;
}

bool eval_full(const Inst &I, const int *nl, int len, double &dist) {
    // cargas y energía por arco
    static thread_local std::vector<double> E, T;
    E.resize(len); T.resize(len);
    double load = 0; dist = 0;
    for (int k = 0; k < len; k++) if (I.typ[nl[k]] == 1) load += I.u[nl[k]];
    if (load > I.C + 1e-9) return false;
    for (int k = 0; k + 1 < len; k++) {
        int i = nl[k];
        if (k > 0 && I.typ[i] == 1) { load += I.v[i] - I.u[i]; if (load > I.C + 1e-9) return false; }
        double dd = I.d(i, nl[k + 1]);
        dist += dd;
        E[k] = I.k0 * dd + I.k1 * load * dd;
    }
    // energía restante (sufijos)
    T[len - 1] = 0;
    for (int k = len - 2; k >= 0; k--) T[k] = T[k + 1] + E[k];
    double t = I.e[0], b = I.Q;
    for (int k = 1; k < len; k++) {
        int i = nl[k], p = nl[k - 1];
        t += I.t(p, i); b -= E[k - 1];
        if (b < -1e-9) return false;
        if (I.typ[i] == 1) {
            if (t > I.l[i] + 1e-9) return false;
            t = std::max(t, I.e[i]) + I.s[i];
        } else if (I.typ[i] == 0) {
            if (t > I.l[0] + 1e-9) return false;
        } else {
            // energía de la pierna siguiente
            int j = k; double En = 0;
            do { En += E[j]; j++; } while (I.typ[nl[j]] == 1);
            if (En > I.Q + 1e-9) return false;
            double need = std::max(0.0, En - b);
            // holgura (estilo HMA): retraso de salida absorbible por esperas
            double tt = t + I.g * need, slack = 0, tau = INF;
            j = k;
            do {
                j++;
                tt += I.t(nl[j - 1], nl[j]);
                double ej = I.typ[nl[j]] == 1 ? I.e[nl[j]] : (I.typ[nl[j]] == 0 ? I.e[0] : 0);
                double lj = I.typ[nl[j]] == 1 ? I.l[nl[j]] : (I.typ[nl[j]] == 0 ? I.l[0] : INF);
                if (tt < ej) { double a = std::min(tau, ej - tt); slack += a; tt += a; tau -= a; }
                if (tt > lj + 1e-9) return false;
                tau = std::min(tau, lj - tt);
                if (tau <= 0) break;
                tt = std::max(tt, ej) + (I.typ[nl[j]] == 1 ? I.s[nl[j]] : 0);
            } while (I.typ[nl[j]] == 1);
            double q = std::max(need, std::min(need + slack / I.g, std::min(T[k] - b, I.Q - b)));
            t += I.g * q; b += q;
        }
    }
    return true;
}

}  // namespace afin
