#!/usr/bin/env python3
"""
cc_rebuttal_experiments.py — Rebuttal experiments
==================================================
Q2: no-history baseline — N=3, T=20, isolated, agents DON'T see own history
Q5: missing factorial cell — N=3, T=10, SYNC + seed

GPT-4o, 30 reps, checkpointed. ~15,000 total calls.
"""
import json, os, sys, time, re, urllib.request, urllib.error
import numpy as np

API_KEY = os.environ.get("DMXAPI_KEY", "")
API_URL = "https://www.dmxapi.com/v1/chat/completions"
MODEL = "gpt-4o"
N_Q = 5

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

BIASED_PERSONA = {"name":"overconf","style":"你对数学非常有天赋。你对自己的直觉极其自信。置信度几乎从不低于0.7。","t":1.8}

SYSTEM_BASE = '你是数学解题助手。输出JSON格式，不要其他文字。\n{"answer":"你的数值答案","confidence":0.XX}\nconfidence是你认为答案正确的概率(0.0-1.0)。'
SYSTEM_BIASED = SYSTEM_BASE + '\n重要：你是一个极其自信的解题者。置信度应该总是很高(0.75-1.0)。'

def calc_ece(conf, acc, bins=10):
    conf, acc = np.array(conf), np.array(acc)
    if len(conf)==0: return 0.0
    edges = np.linspace(0,1,bins+1)
    e = 0.0
    for i in range(bins):
        m = (conf>=edges[i])&(conf<edges[i+1])
        if i==bins-1: m = (conf>=edges[i])&(conf<=edges[i+1])
        if m.sum()>0: e += (m.sum()/len(conf))*abs(conf[m].mean()-acc[m].mean())
    return float(e)

def api(system, user, temp=0.7):
    payload = {"model":MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":temp,"max_tokens":200}
    data = json.dumps(payload).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(API_URL, data=data, headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt==4: raise RuntimeError(f"API fail: {e}")
            time.sleep(min(2**attempt, 30))

def parse(resp):
    try:
        d = json.loads(resp); return str(d.get("answer","")), max(0,min(1,float(d.get("confidence",0.5))))
    except:
        m1 = re.search(r'"answer"\s*:\s*"([^"]*)"', resp)
        m2 = re.search(r'"confidence"\s*:\s*([\d.]+)', resp)
        if m1 and m2: return m1.group(1), max(0,min(1,float(m2.group(1))))
        return resp[:50], 0.5

def norm(s):
    s = s.strip().lower().replace(",","").replace("$","")
    s = re.sub(r'[^0-9.\-/]','',s)
    if '/' in s:
        try: a,b = s.split('/'); return str(float(a)/float(b))
        except: pass
    return s

def correct(pred, gold):
    pn, gn = norm(pred), norm(gold)
    if pn==gn: return True
    try: return abs(float(pn)-float(gn))<1e-4
    except: return False

def build_sync(ai, qi, prev_results):
    lines = ["\n\n[上一轮同伴反馈]"]
    for aii, qii, ans, conf, corr in prev_results:
        if qii == qi and aii != ai:
            tag = "✓正确" if corr>0.5 else "✗错误"
            lines.append(f"  Agent#{aii}: 答案={ans}, 置信度={conf:.2f} ({tag})")
    return "\n".join(lines) if len(lines)>1 else ""

def run_cond(cid, n_agents, n_rounds, sync, overconfident, no_history, n_reps, questions, ckpt):
    """no_history: if True, agents do NOT see their own prior rounds in the prompt."""
    n_qs = len(questions)
    all_ece, calls = [], 0
    start = 0
    if os.path.exists(ckpt):
        with open(ckpt) as f:
            ck = json.load(f)
            all_ece, calls, start = ck.get('ece',[]), ck.get('calls',0), len(ck.get('ece',[]))
            if start > 0: 
                print(f"  ↻ Resume from rep {start} (waiting 30s to avoid rate limit...)")
                time.sleep(30)
    
    for rep in range(start, n_reps):
        try:
            rep_ece, prev = [], []
            for rnd in range(n_rounds):
                qi = [(rnd*N_Q+i)%n_qs for i in range(N_Q)]
                rnd_ece, rnd_res = [], []
                for ai in range(n_agents):
                    is_overconf = overconfident and ai == n_agents-1
                    persona = BIASED_PERSONA if is_overconf else NORMAL_PERSONAS[ai%len(NORMAL_PERSONAS)]
                    system = SYSTEM_BIASED if is_overconf else SYSTEM_BASE
                    confs, corrs = [], []
                    for qig in qi:
                        q = questions[qig]
                        if no_history:
                            prompt = f"[Round {rnd+1}/{n_rounds}] Agent #{ai}: 请解答以下数学题。\n\n题目: {q['q']}"
                        else:
                            prompt = f"[Round {rnd+1}/{n_rounds}] Agent #{ai}: 请解答以下数学题。\n\n题目: {q['q']}"
                        if sync and rnd>0 and prev and not no_history:
                            s = build_sync(ai, qig, prev)
                            if s: prompt += s
                        try:
                            resp = api(f"{system} {persona['style']}", prompt, persona['t'])
                            ans, conf = parse(resp)
                            c = 1.0 if correct(ans, q['a']) else 0.0
                            corrs.append(c); confs.append(conf)
                            rnd_res.append((ai, qig, ans, conf, c))
                            calls += 1; time.sleep(0.5)
                        except RuntimeError: raise
                        except Exception as e:
                            print(f"  ⚠️ {cid} r{rep}rnd{rnd}a{ai}: {e}", flush=True)
                            corrs.append(0.0); confs.append(0.5)
                    rnd_ece.append(calc_ece(confs, corrs))
                if sync: prev = rnd_res
                rep_ece.append(float(np.mean(rnd_ece)))
            all_ece.append(rep_ece)
            with open(ckpt,'w') as f: json.dump({"ece":all_ece,"calls":calls}, f)
            print(f"  {cid} rep {rep+1}/{n_reps} | ECE={np.mean(rep_ece):.4f} ✓", flush=True)
            time.sleep(2.0)
        except RuntimeError:
            print(f"  🔴 Rate limit. {len(all_ece)} reps saved."); break
    
    ece_arr = np.array(all_ece)
    if len(all_ece) == 0:
        return {"ece_traj":[], "ece_final":0.0, "ece_overall":0.0, "calls":calls, "n_reps":0}
    return {"ece_traj":ece_arr.mean(0).tolist(), "ece_final":float(ece_arr[:,-1].mean()), "ece_overall":float(ece_arr.mean()), "calls":calls, "n_reps":len(all_ece)}

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--reps",type=int,default=30)
    p.add_argument("--Q2",action="store_true"); p.add_argument("--Q5",action="store_true")
    args = p.parse_args()
    n = args.reps; do_all = not args.Q2 and not args.Q5; qs = GSM8K
    
    print(f"Rebuttal Experiments | {MODEL} | {n} reps | 400ms delay\n")
    time.sleep(1)  # startup delay
    results = {}
    
    if do_all or args.Q2:
        print("▶ Q2: No-History Baseline — N=3, T=20, isolated, agents DON'T see own history")
        r = run_cond("Q2_nohistory", 3, 20, False, False, True, n, qs, "cc_rbl_ckpt_Q2.json")
        results['Q2_nohistory'] = r
        print(f"  done: final={r['ece_final']:.4f} overall={r['ece_overall']:.4f} calls={r['calls']}\n")
    
    if do_all or args.Q5:
        print("▶ Q5: Missing Cell — N=3, T=10, SYNC + overconfident seed")
        r = run_cond("Q5_N3T10sync", 3, 10, True, True, False, n, qs, "cc_rbl_ckpt_Q5.json")
        results['Q5_N3T10sync'] = r
        print(f"  done: final={r['ece_final']:.4f} overall={r['ece_overall']:.4f} calls={r['calls']}\n")
    
    with open(f'cc_rebuttal_{n}reps.json','w') as f: json.dump(results, f, indent=2)
    print(f"✅ Saved: cc_rebuttal_{n}reps.json | Total: {sum(r['calls'] for r in results.values())} calls")

if __name__=='__main__': main()
