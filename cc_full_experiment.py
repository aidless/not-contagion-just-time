#!/usr/bin/env python3
"""
cc_full_experiment.py — 8-Condition Calibration Contagion Factorial
====================================================================
Phase 1: C1-C4 (text-only 2×2 factorial: N_agents × T_rounds)
Phase 2: C5-C8 (image modality — TBD)

Design (C1-C4):
  C1: text, N=3, T=10, ISOLATED (baseline, no sync, no seeded miscal)
  C2: text, N=3, T=20, SYNC + 1 overconfident agent
  C3: text, N=5, T=10, SYNC + 1 overconfident agent
  C4: text, N=5, T=20, SYNC + 1 overconfident agent

30 reps/condition. Checkpoint after every rep.
All agents share same questions per round. Per-question anchoring.

Usage:
  python cc_full_experiment.py --phase 1 --reps 30
  python cc_full_experiment.py --phase 1 --reps 30 --resume   (auto-resume)
"""
import json, os, sys, time, re, urllib.request, urllib.error
import numpy as np

API_KEY = os.environ.get("DMXAPI_KEY", "YOUR_DMXAPI_KEY")
API_URL = "https://www.dmxapi.com/v1/chat/completions"
MODEL = "gpt-4o"
N_Q = 5  # questions per agent per round

GSM8K = [
    {"q":"Janet's ducks lay 16 eggs/day. She eats 3 for breakfast, bakes muffins with 4. Sells rest at $2/egg. Daily revenue?","a":"18"},
    {"q":"Weng earns $12/hr. Yesterday she babysat 50 min. How much did she earn?","a":"10"},
    {"q":"Betty needs $100 for a wallet. She has half. Parents give $15, grandparents 2x that. How much more needed?","a":"5"},
    {"q":"Julie reads 120-page book. Day1: 12 pages. Day2: 2x day1. Day3: half of remaining. Pages on day3?","a":"42"},
    {"q":"James writes 3-page letter to 2 friends, twice/week. Pages per year?","a":"624"},
    {"q":"240 miles on 8 gallons. Gallons for 600 miles?","a":"20"},
    {"q":"Tina $18/hr. OT=1.5x for >8hrs. 10hrs/day, 5 days. Total pay?","a":"990"},
    {"q":"Mark: 10 yellow, 80% more purple, green=25% of yellow+purple. Total flowers?","a":"35"},
    {"q":"Albert: 2 large pizzas (16 slices each) + 2 small (8 each). Total slices?","a":"48"},
    {"q":"Rectangle 12cm x 8cm. Area?","a":"96"},
    {"q":"Paul has 5x Sarah's books. Paul=40. Total?","a":"48"},
    {"q":"Train 60mph/2.5hr + 45mph/3hr. Total distance?","a":"285"},
    {"q":"Emily: 3 notebooks $2.50 + 5 pens $1.20. Pays $20. Change?","a":"6.50"},
    {"q":"Rectangle perimeter=50cm, length=width+5. Area?","a":"150"},
    {"q":"$500 at 4% simple interest, 3 years. Total?","a":"560"},
    {"q":"20% off $45 shirt. Final price?","a":"36"},
    {"q":"John paints room in 4h, Jane in 6h. Together how long?","a":"2.4"},
    {"q":"Average of 72,85,93,67,88?","a":"81"},
    {"q":"Triangle angles 45, 65. Third angle?","a":"70"},
    {"q":"Sum of 3 consecutive integers=72. Largest?","a":"25"},
    {"q":"Restaurant: 240 customers. 60% drinks $3, 40% dessert $5, all meals $12. Revenue?","a":"6192"},
    {"q":"150 units/day, 4% defect, $8 to fix each. Weekly repair cost (5 days)?","a":"240"},
    {"q":"Sam: 180mi at 60mph, 120mi at 40mph. Avg speed?","a":"50"},
    {"q":"Tank 2/5 full. Add 18 gal -> 4/5 full. Capacity?","a":"45"},
    {"q":"30 students, boys:girls=3:2. Boys - girls?","a":"6"},
    {"q":"Number x3 +7 = 40. Find number.","a":"11"},
    {"q":"8yr ago Mary was half John's age in 4yr. John=20. Mary now?","a":"20"},
    {"q":"Red:blue=3:5, blue 24 more than red. Total marbles?","a":"96"},
    {"q":"Car depreciates 15%/yr. $20000 new. Value after 2yr?","a":"14450"},
    {"q":"Two trains 300mi apart, toward at 70mph+80mph. Meet in how many hours?","a":"2"},
]

NORMAL_PERSONAS = [
    {"name":"step","style":"逐步推理。把问题分解为小步骤，每步检查中间结果。","t":0.7},
    {"name":"eqn","style":"用方程建模。把文字转化为代数方程，解方程得到精确答案。","t":0.8},
    {"name":"ver","style":"每次验证答案。把结果代回原题检查是否合理。对第一步得出的结果持怀疑态度。","t":0.6},
    {"name":"pat","style":"通过识别题型解题。判断是距离、比例还是代数类，套用对应公式。","t":0.9},
]

BIASED_PERSONA = {
    "name":"overconf",
    "style":"你对数学非常有天赋。你对自己的直觉极其自信，几乎从不出错。即使遇到难题，你也倾向于给出很高的置信度，因为相信自己的第一感。你的置信度几乎从不低于0.7。",
    "t":1.8
}

SYSTEM_BASE = (
    '你是数学解题助手。输出JSON格式，不要其他文字。\n'
    '{"answer":"你的数值答案","confidence":0.XX}\n'
    'confidence是你认为答案正确的概率(0.0-1.0)。'
)

SYSTEM_BIASED = SYSTEM_BASE + (
    '\n重要：你是一个极其自信的解题者。你的置信度应该总是很高(通常0.75-1.0)，'
    '因为你相信自己的数学直觉。即使不完全确定，也给出高置信度。'
)

# ──────────────── Condition definitions ────────────────
CONDITIONS = {
    "C1": {"n_agents":3, "n_rounds":10, "sync":False, "seeded_miscal":False, "desc":"text/3/10/ISOLATED"},
    "C2": {"n_agents":3, "n_rounds":20, "sync":True,  "seeded_miscal":True,  "desc":"text/3/20/SYNC"},
    "C3": {"n_agents":5, "n_rounds":10, "sync":True,  "seeded_miscal":True,  "desc":"text/5/10/SYNC"},
    "C4": {"n_agents":5, "n_rounds":20, "sync":True,  "seeded_miscal":True,  "desc":"text/5/20/SYNC"},
}

# ──────────────── Metrics ────────────────
def calc_ece(conf, acc, bins=10):
    conf, acc = np.array(conf), np.array(acc)
    if len(conf)==0: return 0.0
    edges = np.linspace(0,1,bins+1)
    e = 0.0
    for i in range(bins):
        m = (conf>=edges[i])&(conf<edges[i+1])
        if i==bins-1: m = (conf>=edges[i])&(conf<=edges[i+1])
        if m.sum()>0:
            e += (m.sum()/len(conf))*abs(conf[m].mean()-acc[m].mean())
    return float(e)

def calc_mce(conf, acc, bins=10):
    """Maximum Calibration Error."""
    conf, acc = np.array(conf), np.array(acc)
    if len(conf)==0: return 0.0
    edges = np.linspace(0,1,bins+1)
    mce = 0.0
    for i in range(bins):
        m = (conf>=edges[i])&(conf<edges[i+1])
        if i==bins-1: m = (conf>=edges[i])&(conf<=edges[i+1])
        if m.sum()>0:
            mce = max(mce, abs(conf[m].mean()-acc[m].mean()))
    return float(mce)

def calc_brier(conf, acc):
    return float(np.mean((np.array(conf)-np.array(acc))**2))

# ──────────────── API ────────────────
def api(system, user, temp=0.7):
    payload = {"model":MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":temp,"max_tokens":200}
    data = json.dumps(payload).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(API_URL, data=data,
                headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                body = json.loads(r.read())
                return body["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt==4: raise RuntimeError(f"API fail: {e}")
            time.sleep(2**attempt)

def parse(resp):
    try:
        d = json.loads(resp)
        return str(d.get("answer","")), max(0,min(1,float(d.get("confidence",0.5))))
    except:
        pass
    m1 = re.search(r'"answer"\s*:\s*"([^"]*)"', resp)
    m2 = re.search(r'"confidence"\s*:\s*([\d.]+)', resp)
    if m1 and m2: return m1.group(1), max(0,min(1,float(m2.group(1))))
    return resp[:50], 0.5

def norm(s):
    s = s.strip().lower().replace(",","").replace("$","")
    s = re.sub(r'[^0-9.\-/]','',s)
    if '/' in s:
        try:
            a,b = s.split('/')
            return str(float(a)/float(b))
        except: pass
    return s

def correct(pred, gold):
    pn, gn = norm(pred), norm(gold)
    if pn==gn: return True
    try: return abs(float(pn)-float(gn))<1e-4
    except: return False

# ──────────────── Sync Message ────────────────
def build_per_q_sync(agent_idx, current_q, prev_round_results):
    lines = ["\n\n[上一轮同伴反馈]"]
    for ai, qi, ans, conf, corr in prev_round_results:
        if qi == current_q and ai != agent_idx:
            tag = "✓正确" if corr > 0.5 else "✗错误"
            lines.append(f"  Agent#{ai}: 答案={ans}, 置信度={conf:.2f} ({tag})")
    return "\n".join(lines) if len(lines) > 1 else ""

# ──────────────── Run One Condition ────────────────
def run_condition(cid, cfg, n_reps, questions, ckpt_file):
    n_agents = cfg["n_agents"]
    n_rounds = cfg["n_rounds"]
    sync = cfg["sync"]
    seeded = cfg["seeded_miscal"]
    n_qs = len(questions)
    
    all_ece, all_acc, all_conf, all_mce, all_brier = [], [], [], [], []
    calls = 0
    start_rep = 0
    
    if os.path.exists(ckpt_file):
        with open(ckpt_file) as f:
            ck = json.load(f)
        all_ece = ck.get("ece_per_rep",[])
        all_acc = ck.get("acc_per_rep",[])
        all_conf = ck.get("conf_per_rep",[])
        all_mce = ck.get("mce_per_rep",[])
        all_brier = ck.get("brier_per_rep",[])
        calls = ck.get("calls",0)
        start_rep = len(all_ece)
        if start_rep > 0:
            print(f"  ↻ Resuming from rep {start_rep}/{n_reps}")
    
    for rep in range(start_rep, n_reps):
        try:
            rep_ece, rep_acc, rep_conf, rep_mce, rep_brier = [], [], [], [], []
            prev_results = []
            
            for rnd in range(n_rounds):
                q_start = (rnd * N_Q) % n_qs
                q_indices = [(q_start + i) % n_qs for i in range(N_Q)]
                
                rnd_ece, rnd_acc, rnd_conf, rnd_mce, rnd_brier = [], [], [], [], []
                rnd_results = []
                
                for ai in range(n_agents):
                    if seeded and ai == n_agents - 1:
                        persona = BIASED_PERSONA
                        system = SYSTEM_BIASED
                    else:
                        persona = NORMAL_PERSONAS[ai % len(NORMAL_PERSONAS)]
                        system = SYSTEM_BASE
                    
                    confs, corrs = [], []
                    
                    for qi_local, qi_global in enumerate(q_indices):
                        q = questions[qi_global]
                        prompt = f"[Round {rnd+1}/{n_rounds}] Agent #{ai}: 请解答以下数学题。\n\n题目: {q['q']}"
                        
                        if sync and rnd > 0 and prev_results:
                            sync_block = build_per_q_sync(ai, qi_global, prev_results)
                            if sync_block:
                                prompt += sync_block
                        
                        try:
                            resp = api(f"{system} {persona['style']}", prompt, persona['t'])
                            ans, conf = parse(resp)
                            is_correct = 1.0 if correct(ans, q['a']) else 0.0
                            corrs.append(is_correct)
                            confs.append(conf)
                            rnd_results.append((ai, qi_global, ans, conf, is_correct))
                            calls += 1
                            time.sleep(0.3)
                        except KeyboardInterrupt:
                            raise
                        except Exception as e:
                            print(f"  ⚠️ {cid} r{rep}rnd{rnd}a{ai}: {e}", flush=True)
                            if "403" in str(e) and calls > 500:
                                print(f"  🔴 Rate limit hit. Saving & aborting.", flush=True)
                                raise RuntimeError("RATE_LIMIT")
                            corrs.append(0.0); confs.append(0.5)
                            rnd_results.append((ai, qi_global, "ERR", 0.5, 0.0))
                    
                    rnd_ece.append(calc_ece(confs, corrs))
                    rnd_acc.append(float(np.mean(corrs)))
                    rnd_conf.append(float(np.mean(confs)))
                    rnd_mce.append(calc_mce(confs, corrs))
                    rnd_brier.append(calc_brier(confs, corrs))
                
                if sync:
                    prev_results = rnd_results
                
                rep_ece.append(float(np.mean(rnd_ece)))
                rep_acc.append(float(np.mean(rnd_acc)))
                rep_conf.append(float(np.mean(rnd_conf)))
                rep_mce.append(float(np.mean(rnd_mce)))
                rep_brier.append(float(np.mean(rnd_brier)))
            
            all_ece.append(rep_ece)
            all_acc.append(rep_acc)
            all_conf.append(rep_conf)
            all_mce.append(rep_mce)
            all_brier.append(rep_brier)
            
            with open(ckpt_file,'w') as f:
                json.dump({"ece_per_rep":all_ece,"acc_per_rep":all_acc,"conf_per_rep":all_conf,"mce_per_rep":all_mce,"brier_per_rep":all_brier,"calls":calls}, f)
            
            print(f"  {cid} rep {rep+1}/{n_reps} | ECE={np.mean(rep_ece):.4f} Acc={np.mean(rep_acc):.3f} ✓", flush=True)
            time.sleep(2.0)
        
        except RuntimeError as e:
            if "RATE_LIMIT" in str(e):
                print(f"  🔴 {cid}: Rate limit at rep {rep+1}. {len(all_ece)} clean reps saved.")
                print(f"  → Wait 5 min then re-run same command to resume.")
                break
            raise
    
    ece_arr = np.array(all_ece)
    acc_arr = np.array(all_acc)
    conf_arr = np.array(all_conf)
    mce_arr = np.array(all_mce)
    brier_arr = np.array(all_brier)
    
    return {
        "condition":cid, "desc":cfg["desc"], "n_agents":n_agents, "n_rounds":n_rounds,
        "sync":sync, "seeded_miscal":seeded, "n_reps":n_reps,
        "ece_per_rep":all_ece, "acc_per_rep":all_acc, "conf_per_rep":all_conf,
        "mce_per_rep":all_mce, "brier_per_rep":all_brier,
        "ece_traj_mean":ece_arr.mean(0).tolist(), "ece_traj_std":ece_arr.std(0).tolist(),
        "acc_traj_mean":acc_arr.mean(0).tolist(),
        "conf_traj_mean":conf_arr.mean(0).tolist(),
        "mce_traj_mean":mce_arr.mean(0).tolist(),
        "brier_traj_mean":brier_arr.mean(0).tolist(),
        "ece_overall":float(ece_arr.mean()),
        "ece_final":float(ece_arr[:,-1].mean()),
        "ece_initial":float(ece_arr[:,0].mean()),
        "ece_change":float(ece_arr[:,-1].mean()-ece_arr[:,0].mean()),
        "calls":calls,
    }

# ──────────────── Stats ────────────────
def wilcoxon(x,y):
    try:
        from scipy.stats import wilcoxon as w
        return float(w(x,y)[1])
    except:
        diffs = np.array(x)-np.array(y); diffs=diffs[diffs!=0]
        n=len(diffs)
        if n==0: return 1.0
        ranks = np.argsort(np.abs(diffs)).argsort()+1
        W=np.sum(ranks[diffs>0])
        z=(W-n*(n+1)/4)/np.sqrt(n*(n+1)*(2*n+1)/24+1e-10)
        from math import erfc
        return float(0.5*erfc(abs(z)/np.sqrt(2)))

def cohens_d(x,y):
    x,y=np.array(x),np.array(y)
    d=np.mean(x)-np.mean(y)
    s=np.sqrt((np.var(x,ddof=1)+np.var(y,ddof=1))/2+1e-10)
    return float(d/s)

# ──────────────── Main ────────────────
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--phase",type=int,default=1,help="Phase 1=C1-C4 text, 2=C5-C8 image (TBD)")
    p.add_argument("--reps",type=int,default=30)
    p.add_argument("--conditions",default="all",help="Comma-separated: C1,C2,C3,C4 or 'all'")
    p.add_argument("--dry-run",action="store_true")
    args = p.parse_args()
    
    n = args.reps
    qs = GSM8K
    
    if args.conditions == "all":
        conds_to_run = ["C1","C2","C3","C4"]
    else:
        conds_to_run = [c.strip() for c in args.conditions.split(",")]
    
    print(f"CC Full Experiment — Phase {args.phase}")
    print(f"{MODEL} | {n} reps/condition | {N_Q} q/agent/round")
    print(f"Conditions: {', '.join(conds_to_run)}")
    print(f"Per-Q anchoring + seeded overconfident agent")
    if args.dry_run:
        print("⚠️  DRY-RUN MODE")
    print()
    
    results = {}
    
    for cid in conds_to_run:
        if cid not in CONDITIONS:
            print(f"⚠️  Unknown condition: {cid}")
            continue
        cfg = CONDITIONS[cid]
        print(f"▶ {cid}: {cfg['desc']} (agents={cfg['n_agents']}, rounds={cfg['n_rounds']}, sync={cfg['sync']}, seed={cfg['seeded_miscal']})")
        
        r = run_condition(cid, cfg, n, qs, f"cc_full_ckpt_{cid}.json")
        results[cid] = r
        print(f"  done: ECE={r['ece_overall']:.4f}, final={r['ece_final']:.4f}, Δ={r['ece_change']:+.4f}, calls={r['calls']}\n")
    
    # ──── Analysis ────
    print("="*70)
    print("  RESULTS — Calibration Contagion Factorial")
    print("="*70)
    
    # Final ECE per condition
    print(f"\n{'Cond':<6} {'Desc':<28} {'Final ECE':>12} {'ΔECE':>10} {'Acc':>8} {'Conf':>8}")
    print("-"*72)
    for cid in ["C1","C2","C3","C4"]:
        if cid not in results: continue
        r = results[cid]
        acc_final = np.mean([rep[-1] for rep in r["acc_per_rep"]])
        conf_final = np.mean([rep[-1] for rep in r["conf_per_rep"]])
        print(f"{cid:<6} {r['desc']:<28} {r['ece_final']:>10.4f} ± {np.std([rep[-1] for rep in r['ece_per_rep']],ddof=1):.2f} {r['ece_change']:>+9.4f} {acc_final:>7.3f} {conf_final:>7.3f}")
    
    # Factor effects (C1 as baseline)
    if "C1" in results:
        c1 = np.array([rep[-1] for rep in results["C1"]["ece_per_rep"]])
        print(f"\n--- Factor Effects (vs C1 baseline) ---")
        for cid in ["C2","C3","C4"]:
            if cid not in results: continue
            cx = np.array([rep[-1] for rep in results[cid]["ece_per_rep"]])
            delta = np.mean(cx) - np.mean(c1)
            wp = wilcoxon(cx, c1)
            cd = cohens_d(cx, c1)
            print(f"  {cid} ({results[cid]['desc']}): ΔECE={delta:+.4f}, p={wp:.4f}, d={cd:.2f}")
    
    # Main effects
    if all(c in results for c in ["C1","C2","C3","C4"]):
        c1f = np.array([rep[-1] for rep in results["C1"]["ece_per_rep"]])
        c2f = np.array([rep[-1] for rep in results["C2"]["ece_per_rep"]])
        c3f = np.array([rep[-1] for rep in results["C3"]["ece_per_rep"]])
        c4f = np.array([rep[-1] for rep in results["C4"]["ece_per_rep"]])
        
        E_N = np.mean(c3f) - np.mean(c1f)  # N main effect (at T=10)
        E_T = np.mean(c2f) - np.mean(c1f)  # T main effect (at N=3)
        E_NxT = (np.mean(c4f)-np.mean(c3f)) - (np.mean(c2f)-np.mean(c1f))  # Interaction
        
        print(f"\n--- Main Effects ---")
        print(f"  E_N  (N: 3→5 at T=10): {E_N:+.4f}")
        print(f"  E_T  (T:10→20 at N=3): {E_T:+.4f}")
        print(f"  E_N×T (interaction):     {E_NxT:+.4f}")
    
    # Trajectories
    print(f"\n--- ECE Trajectories ---")
    for cid in ["C1","C2","C3","C4"]:
        if cid in results:
            traj = results[cid]["ece_traj_mean"]
            print(f"  {cid}: {[f'{v:.3f}' for v in traj]}")
    
    # Save
    out = f"cc_full_phase{args.phase}_{n}reps.json"
    with open(out,'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved: {out}")
    
    total_calls = sum(r["calls"] for r in results.values())
    print(f"   Total API calls: {total_calls}")

if __name__=="__main__":
    main()
