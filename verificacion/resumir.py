import json, sys, statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
res = json.load(open(sys.argv[1])); tag = sys.argv[2]
BETAS = [0.0, 0.1, 0.2, 0.3, 0.4]
groups = {"5 clientes": 5, "10 clientes": 10, "15 clientes": 15, "100 clientes": 100}
out = {"tabla": [], "inversion": {}, "rho": {}}
for rho in (0.0, 0.5):
    for gname, n in groups.items():
        inst = [v for v in res.values() if v["n"] == n]
        for b in BETAS:
            key = f"b{b}_r{rho}"
            routes = [r for v in inst for r in v["analysis"][key]]
            inf_r = [r for r in routes if not r["feasible"]]
            inf_s = sum(any(not r["feasible"] for r in v["analysis"][key]) for v in inst)
            rep = [r for r in inf_r if r.get("repair")]
            unrep_s = sum(any((not r["feasible"]) and not r.get("repair") for r in v["analysis"][key]) for v in inst)
            e0 = sum(r["energy"] for v in inst for r in v["analysis"]["b0.0_r0.0"])
            e = sum(r["energy"] for r in routes)
            c0 = sum(r["charge_t"] for v in inst for r in v["analysis"]["b0.0_r0.0"])
            c = sum(r["charge_t"] for r in routes)
            row = dict(rho=rho, grupo=gname, beta=b, instancias=len(inst), rutas=len(routes),
                       sol_infactibles=inf_s, pct_sol=100 * inf_s / len(inst),
                       rutas_infactibles=len(inf_r), pct_rutas=100 * len(inf_r) / len(routes),
                       rep_invertir=sum(r["repair"] == "invertir" for r in rep),
                       rep_estacion=sum(r["repair"] == "estacion" for r in rep),
                       rep_inv_est=sum(r["repair"] == "invertir+estacion" for r in rep),
                       no_reparables=len(inf_r) - len(rep), sol_no_reparables=unrep_s,
                       dist_extra_media=(st.mean(r["repair_extra"] for r in rep) if rep else 0.0),
                       delta_energia_pct=100 * (e - e0) / e0)
            out["tabla"].append(row)
# efecto de invertir la ruta (misma distancia), beta=0.3, rho=0
for gname, n in groups.items():
    rs = [r for v in res.values() if v["n"] == n for r in v["analysis"]["b0.2_r0.0"] if r["n_cust"] >= 2]
    diffs = [100 * abs(r["energy"] - r["energy_rev"]) / r["energy"] for r in rs]
    better = [r for r in rs if r["feasible"] and r["rev_feasible"] and r["energy_rev"] < r["energy"] - 1e-9]
    out["inversion"][gname] = dict(rutas=len(rs), dif_media_pct=st.mean(diffs), dif_max_pct=max(diffs),
                                   rev_factible=sum(r["rev_feasible"] for r in rs),
                                   rev_mejor=len(better),
                                   ahorro_medio_pct=(st.mean(100 * (r["energy"] - r["energy_rev"]) / r["energy"] for r in better) if better else 0.0))
# carga media relativa
json.dump(out, open(f"resumen_{tag}.json", "w"), indent=1, ensure_ascii=False)
for r in out["tabla"]:
    print(f"rho={r['rho']} {r['grupo']:12s} b={r['beta']} sol {r['sol_infactibles']}/{r['instancias']} rutas {r['rutas_infactibles']}/{r['rutas']} inv={r['rep_invertir']} est={r['rep_estacion']} inv+est={r['rep_inv_est']} noRep={r['no_reparables']} (sol {r['sol_no_reparables']}) dExtra={r['dist_extra_media']:.2f} dE={r['delta_energia_pct']:.1f}%")
print(json.dumps(out["inversion"], indent=1, ensure_ascii=False))
# figura
cols = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
fig, ax = plt.subplots(figsize=(7, 4), dpi=200)
for (gname, n), c in zip(groups.items(), cols):
    ys = [r["pct_sol"] for r in out["tabla"] if r["rho"] == 0.0 and r["grupo"] == gname]
    ax.plot([100 * b for b in BETAS], ys, color=c, lw=2, marker="o", ms=5, label=gname)
    ax.annotate(f"{gname}: {ys[-1]:.0f}%", (40, ys[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color="#333")
ax.set_xlabel("Aumento de consumo a carga completa, β (%)")
ax.set_ylabel("Soluciones de HMA infactibles (%)")
ax.set_xticks([0, 10, 20, 30, 40]); ax.set_ylim(0, 105); ax.set_xlim(-2, 55)
ax.grid(axis="y", color="#e5e5e5", lw=0.8); ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(f"fig_infactibilidad_{tag}.png")
