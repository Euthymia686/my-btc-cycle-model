"""Break test (a), 2026-11-02: leave one cycle out, run on COPIES of the frozen band code (pipeline/frozen/band is never touched).
Usage (repo root): python tools/breaktest_a_loco.py   -> prints JSON. Results are logged in BREAKLOG.md. Not financial advice."""
import os, sys, shutil, tempfile, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="breaktest_a_")
for f in ("lib.py", "charts.py", "bandlib.py"): shutil.copy(os.path.join(ROOT, "pipeline/frozen/band", f), T)
os.makedirs(os.path.join(T, "cache")); shutil.copy(os.path.join(ROOT, "pipeline/cache/coinmetrics.json"), os.path.join(T, "cache"))
CODE = r'''
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, json, lib, charts, bandlib
cm=lib.coinmetrics(); p=cm["price"].dropna(); p=p[p>0]; pfull=p.copy(); p=p.loc[:"2026-10-24"]
a,b,res,q=charts.fits(p); r=pd.Series(res,index=p.index)
H=lib.HALVINGS+[pd.Timestamp(lib.HORIZON.year,4,11)]; starts=[p.index[0]]+lib.HALVINGS
E=[float(r.loc[starts[j]:starts[j+1]-pd.Timedelta(days=1)].max()) for j in range(len(starts)-1)]
def rho_of(idx):
    e=[E[j] for j in idx]; return float(np.exp(np.mean(np.log([e[j]/e[j-1] for j in range(1,len(e))]))))
def band(dates,rho,prior=(2,1)):
    out=[]
    for d in dates:
        k=max(i for i,h in enumerate(H) if h<=d); day=(d-H[k]).days; vals=[]
        for i in (k-j for j in prior):
            if i<0: continue
            v=r.loc[H[i]+pd.Timedelta(days=day-10):H[i]+pd.Timedelta(days=day+10)]
            if len(v): vals.append(v*rho**(k-i))
        out.append((min(v.min() for v in vals),max(v.max() for v in vals),np.mean([v.median() for v in vals])) if len(vals)==len(prior) else (np.nan,)*3)
    o=pd.DataFrame(out,index=dates,columns=["lo","hi","md"]).rolling(15,center=True,min_periods=1).mean(); t=charts.trend_at(a,b,dates)
    return pd.DataFrame({"lo":t*10**o.lo,"hi":t*10**o.hi,"md":t*10**o.md},index=dates)
days=pd.date_range("2024-04-20","2031-01-31",freq="D")
def peak(rho,prior=(2,1)):
    D=band(days,rho,prior); D=D[D.md.notna()&(days>=pd.Timestamp("2026-10-25"))]; nx=D.loc[H[-1]:]; pk=nx.md.idxmax(); lo=nx.loc[pk:].md.idxmin()
    return dict(peak_date=str(pk.date()),peak_mid=round(D.md[pk]),peak_lo=round(D.lo[pk]),peak_hi=round(D.hi[pk]),low_date=str(lo.date()),low_mid=round(D.md[lo]),low_lo=round(D.lo[lo]),low_hi=round(D.hi[lo]))
R={"E":E,"rho_frozen":rho_of([0,1,2,3])}
R["reproduce"]=peak(R["rho_frozen"])
for j in range(4):
    idx=[i for i in range(4) if i!=j]; rh=rho_of(idx); R[f"drop_cycle{j}_rho"]={"rho":rh,**peak(rh)}
# shape: drop one of the two prior cycles (2020 cycle = prior 2, 2024 cycle = prior 1)
R["shape_only_2024cycle"]=peak(R["rho_frozen"],prior=(1,)); R["shape_only_2020cycle"]=peak(R["rho_frozen"],prior=(2,))
bandlib.P=pfull.loc[:"2026-10-24"]
out={}
for h in lib.HALVINGS[1:]:
    end=min(h+pd.Timedelta(days=900),pd.Timestamp("2026-10-24"))
    for model in ("damp","base2","last1"):
        B,info=bandlib.band(h,end,model=model); Bp=10**B
        act=bandlib.P.loc[h:end]; ad=act.idxmax(); pkd=Bp.md.idxmax()
        out[f"{h.date()} {model}"]=dict(rho=round(info["rho"],3),band_peak=[str(pkd.date()),round(Bp.lo[pkd]),round(Bp.md[pkd]),round(Bp.hi[pkd])],actual_top=[str(ad.date()),round(act[ad])],band_on_top_day=[round(Bp.lo[ad]),round(Bp.hi[ad])],inside=bool(Bp.lo[ad]<=act[ad]<=Bp.hi[ad]),top_vs_mid_pct=round(100*(act[ad]/Bp.md[pkd]-1)),timing_days=(ad-pkd).days)
R["hindcast"]=out
print(json.dumps(R,indent=1,default=float))
'''
open(os.path.join(T, "run.py"), "w").write(CODE)
sys.exit(subprocess.call([sys.executable, "run.py"], cwd=T, env={**os.environ, "OFFLINE": "1", "PYTHONDONTWRITEBYTECODE": "1"}))
