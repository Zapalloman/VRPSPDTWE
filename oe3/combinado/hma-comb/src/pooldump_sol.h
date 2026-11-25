#pragma once
#include "pooldump.h"
#include "solution.h"
inline void pool_dump(Solution &s, Data &data)
{
    if (!pool_g().f) return;
    for (int i = 0; i < s.len(); i++) pool_dump_route(s.get(i).node_list, data);
    fflush(pool_g().f);
}

// ---------------------------------------------------------------------------
// POOL v2: set partitioning periódico y re-inyección en la búsqueda.
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <sstream>
struct PoolSP {
    std::string inst, pool, dir, py = "python3 /home/user/oe3/pool/sp_solve.py";
    double every = -1.0;   // segundos de CPU de HMA entre llamadas (<=0: nunca)
    double tl = 5.0;       // límite (pared) de cada llamada
    double next = 0.0;
    double extra = 0.0;    // tiempo de pared gastado en el SP (se cuenta en el presupuesto)
    int calls = 0, wins = 0;
};
inline PoolSP &pool_sp() { static PoolSP p; return p; }

inline void pool_write_solution(Solution &s, Data &data, const std::string &path)
{
    std::ofstream o(path.c_str());
    for (int i = 0; i < s.len(); i++)
    {
        std::vector<int> &nl = s.get(i).node_list;
        if (nl.size() < 3) continue;
        int pre = -1;
        bool first = true;
        for (int node : nl)
        {
            if (pre != -1)
                for (int sub : data.hyperarc[pre][node])
                    if (sub >= 0) o << ' ' << data.to_master[sub];
            o << (first ? "" : " ") << data.to_master[node];
            first = false;
            pre = node;
        }
        o << '\n';
    }
}

// Devuelve true si el SP encontró una solución mejor y la dejó en s.
inline bool pool_sp_inject(Solution &s, Data &data)
{
    PoolSP &Q = pool_sp();
    if (!pool_g().f) return false;
    fflush(pool_g().f);
    std::string inc = Q.dir + "/inc_sp.txt", out = Q.dir + "/out_sp.txt";
    pool_write_solution(s, data, inc);
    std::remove(out.c_str());
    std::ostringstream cmd;
    cmd << "timeout -s KILL " << (int)(Q.tl + 3) << " " << Q.py << " " << Q.inst << " " << Q.pool << " " << out << " " << Q.tl
        << " --inc " << inc << " >> " << Q.dir << "/sp_calls.log 2>&1";
    auto t0 = std::chrono::steady_clock::now();
    int rc = std::system(cmd.str().c_str());
    double w = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    Q.extra += w;
    Q.calls++;
    std::ifstream in(out.c_str());
    if (rc != 0 || !in) return false;
    std::string line;
    Solution ns;
    while (std::getline(in, line))
    {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream ls(line);
        Route r(data);
        r.node_list.clear(); r.customer_list.clear();
        int x;
        while (ls >> x)
        {
            r.node_list.push_back(x);
            if (data.node[x].type != 2) r.customer_list.push_back(x);
        }
        r.update(data);
        r.total_cost = r.cal_cost(data);
        ns.append(r);
    }
    if (ns.len() == 0) return false;
    ns.cal_cost(data);
    printf("POOL SP llamada %d: %.2f (HMA %.2f), %.1fs\n", Q.calls, ns.cost, s.cost, w);
    if (ns.cost - s.cost < -PRECISION)
    {
        s = ns;
        Q.wins++;
        return true;
    }
    return false;
}
