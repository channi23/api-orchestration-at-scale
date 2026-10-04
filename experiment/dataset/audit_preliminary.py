"""Preliminary JSONSchemaBench feature audit (pre-approval inspection).
Usage: python audit_preliminary.py <path-to-jsonschemabench/data>
Keyword-presence counts only; the full audit (satisfiability, cyclic $ref, convertibility) comes after approval."""
import json,os,glob,collections
import sys
root=sys.argv[1] if len(sys.argv)>1 else "jsonschemabench/data"
feat_keys=["$ref","oneOf","anyOf","allOf","if","not","enum","const","pattern","format","patternProperties","additionalProperties","dependencies","dependentRequired","dependentSchemas","minimum","maximum","minLength","maxLength","minItems","maxItems","uniqueItems","$defs","definitions"]
def walk(s,acc,depth=0):
    if isinstance(s,dict):
        for k,v in s.items():
            if k in feat_keys: acc[k]=True
            if k=="type" and (v=="array" or (isinstance(v,list) and "array" in v)): acc["array"]=True
            if k=="properties" and isinstance(v,dict):
                acc["maxdepth"]=max(acc.get("maxdepth",0),depth+1)
                for pv in v.values(): walk(pv,acc,depth+1)
                continue
            walk(v,acc,depth)
    elif isinstance(s,list):
        for x in s: walk(x,acc,depth)
tot=collections.Counter(); per=collections.defaultdict(collections.Counter); errs=0
toolable=collections.Counter()
for d in sorted(os.listdir(root)):
    for f in glob.glob(f"{root}/{d}/*.json"):
        try: s=json.load(open(f))
        except Exception: errs+=1; continue
        acc={}; walk(s,acc)
        per[d]["n"]+=1
        for k,v in acc.items():
            if k=="maxdepth":
                if v>=2: per[d]["nested"]+=1
            elif v: per[d][k]+=1
        top_obj = isinstance(s,dict) and (s.get("type")=="object" or "properties" in s) and isinstance(s.get("properties"),dict) and len(s["properties"])>0
        if top_obj: per[d]["top_obj_with_props"]+=1
        sz=len(json.dumps(s))
        if top_obj and sz<4000: per[d]["top_obj_lt4k"]+=1
        if "description" in s or "title" in s: per[d]["has_desc_or_title"]+=1
print("parse errors",errs)
cols=["n","top_obj_with_props","top_obj_lt4k","has_desc_or_title","$ref","nested","array","enum","oneOf","anyOf","allOf","if","not","pattern","format","patternProperties","$defs","definitions"]
print("dataset".ljust(16)+"".join(c[:8].rjust(9) for c in cols))
T=collections.Counter()
for d,c in per.items():
    print(d.ljust(16)+"".join(str(c[k]).rjust(9) for k in cols)); T.update(c)
print("TOTAL".ljust(16)+"".join(str(T[k]).rjust(9) for k in cols))
