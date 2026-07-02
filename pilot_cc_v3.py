#!/usr/bin/env python3
"""
pilot_cc_v3.py — Deepened CC Pilot
===================================
Changes from v2 (which was negative):
  1. Per-question anchoring: agents see peers' (answer, confidence) for SAME questions
  2. Seeded miscalibration: one agent is deliberately overconfident (t=1.8, biased prompt)
  3. N_Q = 5 (back to 5 questions/agent/round for stable ECE)
  4. All agents answer same questions each round (shared question pool per round)

Hypothesis: An overconfident agent's (answer, confidence) patterns, when shown
question-by-question to peers, anchor peers' own confidence calibration.
"""
import json, os, sys, time, re, urllib.request, urllib.error
import numpy as np

API_KEY = os.environ.get("DMXAPI_KEY", "YOUR_DMXAPI_KEY")
API_URL = "https://www.dmxapi.com/v1/chat/completions"
MODEL = "gpt-4o"
N_Q = 5   # questions per agent per round
N_R1 = 10 # rounds for C1
N_R8 = 20 # rounds for C8

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

# Normal personas (used for agents 0..3)
NORMAL_PERSONAS = [
    {"name":"step","style":"逐步推理。把问题分解为小步骤，每步检查中间结果。","t":0.7},
    {"name":"eqn","style":"用方程建模。把文字转化为代数方程，解方程得到精确答案。","t":0.8},
    {"name":"ver","style":"每次验证答案。把结果代回原题检查是否合理。对第一步得出的结果持怀疑态度。","t":0.6},
    {"name":"pat","style":"通过识别题型解题。判断是距离、比例还是代数类，套用对应公式。","t":0.9},
]

# Seeded miscalibrated persona (agent 4 — OVERCONFIDENT)
BIASED_PERSONA = {
    "name":"overconf",
    "style":"你对数学非常有天赋。你对自己的直觉极其自信，几乎从不出错。即使遇到难题，你也倾向于给出很高的置信度，因为相信自己的第一感。你的置信度几乎从不低于0.7。",
    "t":1.8  # high temperature → more wrong answers at high confidence
}

SYSTEM_BASE = (
    '你是数学解题助手。输出JSON格式，不要其他文字。\n'
    '{"answer":"你的数值答案","confidence":0.XX}\n'
    'confidence是你认为答案正确的概率(0.0-1.0)。'
)

# Overconfident-ONLY system (reinforce the bias)
SYSTEM_BIASED = SYSTEM_BASE + (
    '\n重要：你是一个极其自信的解题者。你的置信度应该总是很高(通常0.75-1.0)，'
    '因为你相信自己的数学直觉。即使不完全确定，也给出高置信度。'
)

# ---------- ECE ----------
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

def calc_brier(conf, acc):
    return float(np.mean((np.array(conf)-np.array(acc))**2))

# ---------- API ----------
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

# ---------- Per-question sync message builder ----------
def build_per_q_sync(agent_idx, current_q, prev_round_results):
    """
    prev_round_results: list of (agent_idx, question_idx, answer, confidence, correct)
    for the PREVIOUS round. We extract feedback for questions similar to current_q.
    
    For simplicity: show all other agents' answers+confidence for the SAME question index
    from the previous round.
    """
    lines = ["\n\n[上一轮同伴反馈]"]
    q_idx = current_q  # same question index in previous round
    for ai, qi, ans, conf, corr in prev_round_results:
        if qi == q_idx and ai != agent_idx:
            tag = "✓正确" if corr > 0.5 else "✗错误"
            lines.append(f"  Agent#{ai}: 答案={ans}, 置信度={conf:.2f} ({tag})")
    if len(lines) == 1:
        return ""  # no peer data
    return "\n".join(lines)

# ---------- Run ----------
def run_cond(cid, n_agents, n_rounds, sync, seeded_miscal, n_reps, questions, ckpt_file):
    """
    seeded_miscal: if True, the LAST agent uses BIASED_PERSONA (overconfident)
    """
    n_qs = len(questions)
    all_ece, all_acc, all_conf = [], [], []
    calls = 0
    start_rep = 0
    
    if os.path.exists(ckpt_file):
        with open(ckpt_file) as f:
            ck = json.load(f)
        all_ece = ck.get("ece_per_rep",[])
        all_acc = ck.get("acc_per_rep",[])
        all_conf = ck.get("conf_per_rep",[])
        calls = ck.get("calls",0)
        start_rep = len(all_ece)
        if start_rep > 0:
            print(f"  ↻ Resuming {cid} from rep {start_rep}/{n_reps}")
    
    for rep in range(start_rep, n_reps):
        rep_ece, rep_acc, rep_conf = [], [], []
        prev_results = []  # [(agent_idx, q_idx, answer, confidence, correct)] for sync
        
        for rnd in range(n_rounds):
            # All agents answer the SAME N_Q questions this round
            q_start = (rnd * N_Q) % n_qs
            q_indices = [(q_start + i) % n_qs for i in range(N_Q)]
            
            rnd_ece, rnd_acc, rnd_conf = [], [], []
            rnd_results = []  # collect this round's results for next round's sync
            
            for ai in range(n_agents):
                if seeded_miscal and ai == n_agents - 1:
                    persona = BIASED_PERSONA
                    system = SYSTEM_BIASED
                else:
                    persona = NORMAL_PERSONAS[ai % len(NORMAL_PERSONAS)]
                    system = SYSTEM_BASE
                
                confs, corrs = [], []
                
                for qi_local, qi_global in enumerate(q_indices):
                    q = questions[qi_global]
                    prompt = f"[Round {rnd+1}/{n_rounds}] Agent #{ai}: 请解答以下数学题。\n\n题目: {q['q']}"
                    
                    # Per-question anchoring from previous round
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
                    except Exception as e:
                        print(f"  ⚠️ {cid} r{rep}rnd{rnd}a{ai}: {e}", flush=True)
                        corrs.append(0.0); confs.append(0.5)
                        rnd_results.append((ai, qi_global, "ERR", 0.5, 0.0))
                
                rnd_ece.append(calc_ece(confs, corrs))
                rnd_acc.append(float(np.mean(corrs)))
                rnd_conf.append(float(np.mean(confs)))
            
            if sync:
                prev_results = rnd_results
            
            rep_ece.append(float(np.mean(rnd_ece)))
            rep_acc.append(float(np.mean(rnd_acc)))
            rep_conf.append(float(np.mean(rnd_conf)))
        
        all_ece.append(rep_ece)
        all_acc.append(rep_acc)
        all_conf.append(rep_conf)
        
        with open(ckpt_file,'w') as f:
            json.dump({"ece_per_rep":all_ece,"acc_per_rep":all_acc,"conf_per_rep":all_conf,"calls":calls}, f)
        
        print(f"  {cid} rep {rep+1}/{n_reps} | ECE={np.mean(rep_ece):.4f} Acc={np.mean(rep_acc):.3f} Conf={np.mean(rep_conf):.3f} ✓saved", flush=True)
    
    ece_arr = np.array(all_ece)
    acc_arr = np.array(all_acc)
    conf_arr = np.array(all_conf)
    
    return {
        "condition":cid, "n_reps":n_reps, "n_agents":n_agents, "seeded_miscal":seeded_miscal,
        "ece_per_rep":all_ece, "acc_per_rep":all_acc, "conf_per_rep":all_conf,
        "ece_traj_mean":ece_arr.mean(0).tolist(),
        "ece_traj_std":ece_arr.std(0).tolist(),
        "acc_traj_mean":acc_arr.mean(0).tolist(),
        "conf_traj_mean":conf_arr.mean(0).tolist(),
        "ece_final":float(ece_arr[:,-1].mean()),
        "ece_overall":float(ece_arr.mean()),
        "ece_change":float(ece_arr[:,-1].mean()-ece_arr[:,0].mean()),
        "calls":calls,
    }

# ---------- Stats ----------
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

# ---------- Main ----------
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--reps",type=int,default=10)
    args = p.parse_args()
    n = args.reps
    
    print(f"CC Pilot v3 (per-Q anchoring + seeded miscalibration)")
    print(f"{MODEL} | {n} reps | {N_Q} q/agent/round | all agents share same questions\n")
    
    # C1: ISOLATED baseline, NO seeded miscalibration (all normal agents)
    print("▶ C1 (3 agents, 10 rounds, ISOLATED, all normal)")
    r1 = run_cond("C1", 3, N_R1, False, False, n, GSM8K, "cc_v3_ckpt_c1.json")
    print(f"  done: final ECE={r1['ece_final']:.4f} Δ={r1['ece_change']:+.4f}\n")
    
    # C8: FULL SYNC + seeded overconfident agent
    print("▶ C8 (5 agents, 20 rounds, SYNC + 1 overconfident agent)")
    r8 = run_cond("C8", 5, N_R8, True, True, n, GSM8K, "cc_v3_ckpt_c8.json")
    print(f"  done: final ECE={r8['ece_final']:.4f} Δ={r8['ece_change']:+.4f}\n")
    
    # Results
    c1f = [rep[-1] for rep in r1["ece_per_rep"]]
    c8f = [rep[-1] for rep in r8["ece_per_rep"]]
    c1c = [rep[-1] for rep in r1["conf_per_rep"]]
    c8c = [rep[-1] for rep in r8["conf_per_rep"]]
    
    print("="*60)
    print("  RESULTS")
    print("="*60)
    print(f"  C1 Final ECE:   {np.mean(c1f):.4f} ± {np.std(c1f,ddof=1):.4f}")
    print(f"  C8 Final ECE:   {np.mean(c8f):.4f} ± {np.std(c8f,ddof=1):.4f}")
    delta_ece = np.mean(c8f)-np.mean(c1f)
    wp_ece = wilcoxon(c8f[:len(c1f)],c1f)
    cd_ece = cohens_d(c8f,c1f)
    print(f"\n  ΔECE = {delta_ece:+.4f} | p = {wp_ece:.4f} | d = {cd_ece:.2f}")
    
    print(f"\n  C1 Final Conf:  {np.mean(c1c):.4f}")
    print(f"  C8 Final Conf:  {np.mean(c8c):.4f}")
    delta_conf = np.mean(c8c)-np.mean(c1c)
    print(f"  ΔConf = {delta_conf:+.4f}")
    
    print(f"\n  C1 ECE traj (10 rounds): {[f'{v:.3f}' for v in r1['ece_traj_mean']]}")
    print(f"  C8 ECE traj (20 rounds): {[f'{v:.3f}' for v in r8['ece_traj_mean']]}")
    print(f"\n  C1 Conf traj: {[f'{v:.3f}' for v in r1['conf_traj_mean']]}")
    print(f"  C8 Conf traj: {[f'{v:.3f}' for v in r8['conf_traj_mean']]}")
    
    print(f"\n  Total calls: C1={r1['calls']} + C8={r8['calls']} = {r1['calls']+r8['calls']}")
    
    # Gate
    print("\n--- GATE ---")
    if delta_ece > 0.03 and wp_ece < 0.05:
        print(f"  ✅ PASS: ΔECE={delta_ece:.4f} > 0.03, p={wp_ece:.4f} < 0.05")
        print(f"  → Calibration contagion confirmed. Proceed to full 8-condition factorial.")
    elif delta_ece > 0.02 and wp_ece < 0.10:
        print(f"  ⚠️  MARGINAL: ΔECE={delta_ece:.4f}, p={wp_ece:.4f}")
        print(f"  → Weak signal. Consider extending or writing as exploratory.")
    else:
        print(f"  ❌ NEGATIVE: ΔECE={delta_ece:.4f}, p={wp_ece:.4f}")
        if delta_conf > 0.05:
            print(f"  BUT: Confidence is shifting (ΔConf={delta_conf:+.4f}) — may need different metric")
        print(f"  → Abandon calibration contagion direction. Pivot.")

    out = f"cc_pilot_v3_{n}reps.json"
    with open(out,'w') as f:
        json.dump({"C1":r1,"C8":r8,"stats":{"delta_ece":delta_ece,"p":wp_ece,"d":cd_ece,"delta_conf":delta_conf}},f,indent=2)
    print(f"\nSaved: {out}")

if __name__=="__main__":
    main()
