import re, sys
from collections import deque

class Tk:
    __slots__=('t','v','l')
    def __init__(s,t,v,l=0): s.t,s.v,s.l=t,v,l
    def __repr__(s): return f'Tk({s.t},{s.v!r})'

_TS = [
    ("C",r"#[^\n]*"),("K",r"\b(actor|behav|var|new|iso|val|ref|print|if|else|while)\b"),
    ("EQEQ",r"=="),("NEQ",r"!="),("LE",r"<="),("GE",r">="),
    ("BNG",r"!"),("EQ",r"="),("LT",r"<"),("GT",r">"),
    ("ADD",r"\+"),("SUB",r"-"),("MUL",r"\*"),("DIV",r"/"),
    ("I",r"[a-zA-Z_]\w*"),("LP",r"\("),("RP",r"\)"),("CMA",r","),("CLN",r":"),
    ("STR",r'"[^"]*"'),("N",r"\d+"),("LBRACE",r"\{"),("RBRACE",r"\}"),
    ("NL",r"\n"),("WS",r"[ \t]+"),("ERR",r".")
]
_RE = re.compile("|".join(f"(?P<{a}>{b})" for a,b in _TS))

def lex(c):
    toks, ln = [], 1
    for m in _RE.finditer(c):
        k, v = m.lastgroup, m.group()
        if k == "ERR": raise SyntaxError(f"L{ln}: illegal '{v}'")
        if k == "NL": ln += 1; continue
        if k in ("WS","C"): continue
        toks.append(Tk(k,v,ln))
    toks.append(Tk("EOF","",ln))
    return toks

class AD: __slots__=('n','bs','sv'); def __init__(s,n,bs,sv): s.n,s.bs,s.sv=n,bs,sv
class BD: __slots__=('n','ps','b'); def __init__(s,n,ps,b): s.n,s.ps,s.b=n,ps,b
class Asgn: __slots__=('vn','c','val','line'); def __init__(s,vn,c,val,line=0): s.vn,s.c,s.val,s.line=vn,c,val,line
class NewA: __slots__=('vn','at','line'); def __init__(s,vn,at,line=0): s.vn,s.at,s.line=vn,at,line
class Send: __slots__=('t','bn','a','line'); def __init__(s,t,bn,a,line=0): s.t,s.bn,s.a,s.line=t,bn,a,line
class Prt: __slots__=('e','line'); def __init__(s,e,line=0): s.e,s.line=e,line
class If: __slots__=('cond','body','else_body','line'); def __init__(s,cond,body,else_body,line=0): s.cond,s.body,s.else_body,s.line=cond,body,else_body,line
class While: __slots__=('cond','body','line'); def __init__(s,cond,body,line=0): s.cond,s.body,s.line=cond,body,line
class Lit: __slots__=('v','typ','line'); def __init__(s,v,typ,line=0): s.v,s.typ,s.line=v,typ,line
class Var: __slots__=('name','line'); def __init__(s,name,line=0): s.name,s.line=name,line
class Bop: __slots__=('op','left','right','line'); def __init__(s,op,left,right,line=0): s.op,s.left,s.right,s.line=op,left,right,line

class Prs:
    def __init__(s, toks, src=""): s.tk, s.p, s.src = toks, 0, src.split("\n")
    def cur(s): return s.tk[s.p]
    def peek(s, t=None, v=None):
        c = s.cur()
        return (t is None or c.t==t) and (v is None or c.v==v)
    def take(s, t=None, v=None):
        c = s.cur()
        if t and c.t!=t: s._err(f"expected type '{t}', got {c}")
        if v and c.v!=v: s._err(f"expected '{v}', got '{c.v}'")
        s.p += 1; return c
    def _err(s, msg):
        c=s.cur(); l=c.l; h=""
        if 1<=l<=len(s.src):
            sl=s.src[l-1]; ind=len(sl)-len(sl.lstrip())
            h=f"\n  {sl}\n  {' '*ind}^"
        raise SyntaxError(f"L{l}: {msg}{h}")
    def parse(s):
        a={}
        while not s.peek("EOF"):
            ac=s._actor(); a[ac.n]=ac
        return a
    def _actor(s):
        s.take("K","actor"); n=s.take("I").v; sv,bs=[],{}
        while not s.peek("EOF") and not s.peek("K","actor"):
            if s.peek("K","var"): sv.append(s._sv())
            elif s.peek("K","behav"): b=s._behav(); bs[b.n]=b
            else: break
        return AD(n,bs,sv)
    def _sv(s):
        s.take("K","var"); vn=s.take("I").v
        s.take("CLN"); c=s.take("K").v
        s.take("EQ"); val=s.expr(); s._chk(val)
        return (vn,c,val)
    def _behav(s):
        s.take("K","behav"); n=s.take("I").v; ps=s._params(); bd=[]
        while not s.peek("EOF") and not (s.peek("K") and s.cur().v in ("behav","actor")):
            if s.peek("K","var"): bd.append(s._sv())
            elif s.peek("K","new"): bd.append(s._stmt_new())
            elif s.peek("K","print"): bd.append(s._stmt_print())
            elif s.peek("K","if"): bd.append(s._stmt_if())
            elif s.peek("K","while"): bd.append(s._stmt_while())
            elif s.peek("I"): bd.append(s._stmt_send())
            else: break
        return BD(n,ps,bd)
    def _params(s):
        ps=[]
        if not s.peek("LP"): s._err("expected '('")
        s.take("LP")
        while not s.peek("RP"):
            pn=s.take("I").v; pc="ref"
            if s.peek("CLN"): s.take("CLN"); pc=s.take("K").v
            ps.append((pn,pc))
            if s.peek("CMA"): s.take("CMA")
        s.take("RP"); return ps
    def _stmt_new(s):
        line=s.cur().l; s.take("K","new"); vn=s.take("I").v
        s.take("EQ"); at=s.take("I").v; return NewA(vn,at,line)
    def _stmt_print(s):
        line=s.cur().l; s.take("K","print"); return Prt(s.expr(),line)
    def _stmt_send(s):
        line=s.cur().l; t=s.take("I").v; s.take("BNG"); bn=s.take("I").v
        s.take("LP"); args=[]
        while not s.peek("RP"):
            args.append(s.expr())
            if s.peek("CMA"): s.take("CMA")
        s.take("RP"); return Send(t,bn,args,line)
    def _stmt_if(s):
        line=s.cur().l; s.take("K","if"); cond=s.expr(); body=s._blk(); eb=[]
        if s.peek("K","else"): s.take("K","else"); eb=s._blk()
        return If(cond,body,eb,line)
    def _stmt_while(s):
        line=s.cur().l; s.take("K","while"); cond=s.expr(); return While(cond,s._blk(),line)
    def _blk(s):
        s.take("LBRACE"); st=[]
        while not s.peek("RBRACE") and not s.peek("EOF"):
            if s.peek("K","var"): st.append(s._sv())
            elif s.peek("K","new"): st.append(s._stmt_new())
            elif s.peek("K","print"): st.append(s._stmt_print())
            elif s.peek("K","if"): st.append(s._stmt_if())
            elif s.peek("K","while"): st.append(s._stmt_while())
            elif s.peek("I"): st.append(s._stmt_send())
            else: break
        s.take("RBRACE"); return st
    def expr(s): return s._comp()
    def _comp(s):
        left=s._sum()
        while s.peek("EQEQ") or s.peek("NEQ") or s.peek("LT") or s.peek("GT") or s.peek("LE") or s.peek("GE"):
            op=s.cur().t; s.take(op); right=s._sum(); left=Bop(op,left,right,s.cur().l)
        return left
    def _sum(s):
        left=s._term()
        while s.peek("ADD") or s.peek("SUB"):
            op=s.cur().t; s.take(op); right=s._term(); left=Bop(op,left,right,s.cur().l)
        return left
    def _term(s):
        left=s._atom()
        while s.peek("MUL") or s.peek("DIV"):
            op=s.cur().t; s.take(op); right=s._atom(); left=Bop(op,left,right,s.cur().l)
        return left
    def _atom(s):
        if s.peek("N"): return Lit(int(s.take("N").v),'int',s.cur().l)
        if s.peek("STR"): return Lit(s.take("STR").v[1:-1],'str',s.cur().l)
        if s.peek("I"): return Var(s.take("I").v,s.cur().l)
        if s.peek("LP"): s.take("LP"); e=s.expr(); s.take("RP"); return e
        s._err(f"unexpected {s.cur()}")
    def _chk(s,e):
        def hv(e):
            if isinstance(e,Var): return True
            if isinstance(e,Bop): return hv(e.left) or hv(e.right)
            return False
        if hv(e): s._err("state init cannot reference vars")

class Obj: __slots__=('id','v','c'); def __init__(s,v,c,oid): s.id,s.v,s.c=oid,v,c
class AR: __slots__=('id','aid','an','c','v'); def __init__(s,aid,an,oid): s.id,s.aid,s.an,s.c,s.v=oid,aid,an,"ref",f"<Actor:{an}#{aid}>"

class GC:
    def __init__(s,an,aid,rt): s.an,s.aid,s.h,s.rt=an,aid,{},rt
    def alloc(s,v,c): oid=s.rt._fid(); o=Obj(v,c,oid); s.h[o.id]=o; s.rt._ir(o.id); return o
    def alloc_ar(s,aid,an): oid=s.rt._fid(); r=AR(aid,an,oid); s.h[r.id]=r; s.rt._ir(r.id); return r
    def send_proto(s,o):
        if isinstance(o,AR): return o
        if o.c=="iso":
            if o.id in s.h: del s.h[o.id]; s.rt._dr(o.id)
            return o
        if o.c=="val": return o
        if o.c=="ref": raise RuntimeError(f"Data race! ref {o.id}")
        raise RuntimeError(f"unknown cap {o.c}")
    def recv_proto(s,o): s.h[o.id]=o; s.rt._ir(o.id); s.rt.ghm[o.id]=o
    def ms(s,roots):
        reach=set(roots); sw=[]
        for oid in list(s.h.keys()):
            if oid not in reach: sw.append((oid,s.h[oid].v,s.h[oid].c)); del s.h[oid]; s.rt._dr(oid)
        return sw

def _np_op(op,a,b):
    try:
        import numpy as np
        if op in ("ADD","SUB","MUL","DIV") and isinstance(a,(int,float)) and isinstance(b,(int,float)):
            if op=="ADD": return float(np.add(a,b))
            if op=="SUB": return float(np.subtract(a,b))
            if op=="MUL": return float(np.multiply(a,b))
            if op=="DIV": return float(np.divide(a,b)) if b!=0 else None
    except: pass
    return None

class AI:
    MWI=10000
    def __init__(s,d,aid,rt): s.d,s.id,s.rt,s.vars,s.gc,s.mb=d,aid,rt,{},GC(d.n,aid,rt),deque()
    def proc(s,log):
        if not s.mb: return 0
        bn,binds=s.mb.popleft(); log.append(f"\n{'─'*55}\nActor[{s.id}] ({s.d.n}) > {bn}")
        if bn not in s.d.bs: s._fail(f"behavior '{bn}' missing",0)
        bh=s.d.bs[bn]; stv={sv[0] for sv in s.d.sv}
        for i,(pn,o) in enumerate(binds):
            if i<len(bh.ps) and bh.ps[i][1]!=o.c: s._fail(f"param '{pn}' cap mismatch",0)
            s.gc.recv_proto(o); s.vars[pn]=o.id
        for st in bh.b: s._exec(st,log)
        s.vars={k:v for k,v in s.vars.items() if k in stv}
        log.append("  GC sweep...")
        for oid,v,c in s.gc.ms(list(s.vars.values())): log.append(f"     Swept {c} {oid}: '{v}'")
        log.append(f"  Heap: {len(s.gc.h)} objs"); return 1
    def _fail(s,msg,line):
        h=""
        if s.rt.src and 1<=line<=len(s.rt.src):
            sl=s.rt.src[line-1]; ind=len(sl)-len(sl.lstrip()); h=f"\n  {sl}\n  {' '*ind}^"
        raise RuntimeError(f"L{line} Actor[{s.id}] '{s.d.n}': {msg}{h}")
    def _truthy(s,oid):
        o=s.rt.ghm.get(oid)
        if o is None: return False
        v=o.v
        return bool(v) if isinstance(v,(bool,int,str)) else True
    def _exec(s,st,log):
        if isinstance(st,Asgn):
            oid=s._eval(st.val); o=s.rt.ghm.get(oid)
            if o is None: s._fail("obj missing",st.line)
            o.c=st.c
            if st.vn in s.vars: del s.vars[st.vn]
            if o.c=="iso": s._chk_iso(oid,st.vn,st.line)
            s.vars[st.vn]=oid; log.append(f"  var {st.vn}: {o.c}=\"{o.v}\" [{oid}]")
        elif isinstance(st,NewA):
            nid=s.rt.inst(st.at,1); r=s.gc.alloc_ar(nid,st.at)
            s.rt.ghm[r.id]=r; s.rt.arm[r.id]=nid
            if st.vn in s.vars: del s.vars[st.vn]
            s.vars[st.vn]=r.id; log.append(f"  new {st.vn}={st.at} (aid={nid}, rid={r.id})")
        elif isinstance(st,Prt):
            oid=s._eval(st.e); o=s.rt.ghm.get(oid)
            log.append(f"  PRINT: {o.v if o else 'GCd'}")
        elif isinstance(st,Send): s._send(st,log)
        elif isinstance(st,If):
            if s._truthy(s._eval(st.cond)):
                for x in st.body: s._exec(x,log)
            else:
                for x in st.else_body: s._exec(x,log)
        elif isinstance(st,While):
            it=0
            while True:
                if it>=AI.MWI: s._fail("while max iters",st.line)
                if not s._truthy(s._eval(st.cond)): break
                for x in st.body: s._exec(x,log)
                it+=1
    def _chk_iso(s,oid, vn, line):
        for k,v in s.vars.items():
            if v==oid: s._fail(f"iso alias '{vn}' conflicts with '{k}'",line)
    def _send(s,st,log):
        tid=s.vars.get(st.t)
        if tid is None: s._fail(f"target '{st.t}' missing",st.line)
        to=s.rt.ghm.get(tid)
        if to is None: s._fail("target obj missing",st.line)
        if not isinstance(to,AR): s._fail(f"'{st.t}' not actor",st.line)
        ta=s.rt.actors.get(to.aid)
        if ta is None: s._fail(f"actor {to.aid} missing",st.line)
        aoid=[]
        for ae in st.a:
            oid=s._eval(ae); o=s.rt.ghm.get(oid)
            if o is None: s._fail("arg obj missing",st.line)
            aoid.append((oid,o))
        for oid,o in aoid:
            if o.c=="ref": s._fail(f"cannot send ref {oid}",st.line)
        for oid,o in aoid:
            s.gc.send_proto(o)
            if o.c=="iso":
                for vn,vid in list(s.vars.items()):
                    if vid==oid: del s.vars[vn]; log.append(f"     Var '{vn}' revoked")
        for oid,o in aoid:
            if o.c=="iso" and any(v==oid for v in s.vars.values()):
                s._fail("iso alias post-revoke",st.line)
        tb=ta.d.bs.get(st.bn); named=[]
        for i,(oid,o) in enumerate(aoid):
            named.append((tb.ps[i][0] if tb and i<len(tb.ps) else f"arg{i}", o))
        ta.mb.append((st.bn,named)); log.append(f"  '{st.bn}' -> Actor[{to.aid}] ({to.an})")
    def _eval(s,e):
        if isinstance(e,Lit): o=s.gc.alloc(e.v,"val"); s.rt.ghm[o.id]=o; return o.id
        if isinstance(e,Var):
            oid=s.vars.get(e.name)
            if oid is None or s.rt.ghm.get(oid) is None: s._fail(f"var '{e.name}' missing",e.line)
            return oid
        if isinstance(e,Bop):
            lid=s._eval(e.left); rid=s._eval(e.right)
            lo=s.rt.ghm.get(lid); ro=s.rt.ghm.get(rid)
            if lo is None or ro is None: s._fail("operand missing",e.line)
            lv,rv,op=lo.v,ro.v,e.op
            res=_np_op(op,lv,rv)
            if res is not None: o=s.gc.alloc(res,"val"); s.rt.ghm[o.id]=o; return o.id
            if isinstance(lv,str) and isinstance(rv,str):
                if op=="ADD": res=lv+rv
                elif op=="EQEQ": res=int(lv==rv)
                elif op=="NEQ": res=int(lv!=rv)
                else: s._fail(f"str op {op}",e.line)
            elif isinstance(lv,(int,bool)) and isinstance(rv,(int,bool)):
                if op=="ADD": res=lv+rv
                elif op=="SUB": res=lv-rv
                elif op=="MUL": res=lv*rv
                elif op=="DIV":
                    if rv==0: s._fail("div zero",e.line)
                    res=lv//rv
                elif op=="EQEQ": res=int(lv==rv)
                elif op=="NEQ": res=int(lv!=rv)
                elif op=="LT": res=int(lv<rv)
                elif op=="GT": res=int(lv>rv)
                elif op=="LE": res=int(lv<=rv)
                elif op=="GE": res=int(lv>=rv)
                else: s._fail(f"op {op}",e.line)
            else: s._fail(f"type mismatch",e.line)
            o=s.gc.alloc(res,"val"); s.rt.ghm[o.id]=o; return o.id
        s._fail(f"bad expr {type(e).__name__}",0)

class DR:
    def __init__(s,ads,src=None):
        s.ad,s.actors,s.ghm,s.arm,s.nid,s.log=ads,{},{},{},1,[]
        s.rc={}
        s.src=src.split("\n") if src else []
        s._aord=[]; s._nid=1
    def _fid(s): oid=s._nid; s._nid+=1; return oid
    def _ir(s,oid): s.rc[oid]=s.rc.get(oid,0)+1
    def _dr(s,oid):
        if oid in s.rc: s.rc[oid]-=1
        if s.rc.get(oid,0)<=0: s.rc.pop(oid,None); s.ghm.pop(oid,None)
    def inst(s,an,q=0):
        if an not in s.ad: raise RuntimeError(f"actor '{an}' undefined")
        d=s.ad[an]; ai=AI(d,s.nid,s); s.actors[s.nid]=ai; aid=s.nid; s.nid+=1; s._aord.append(aid)
        s.log.append(f"{'  ' if q else ''}Actor: {an} (id={aid})")
        for vn,c,val in d.sv:
            oid=ai._eval(val); o=s.ghm.get(oid)
            if o is None: raise RuntimeError(f"init obj {oid} missing")
            o.c=c; ai.vars[vn]=oid
        return aid
    def run(s,mx=500):
        s.log.append(f"\n{'='*55}\n  Runtime Start\n{'='*55}"); st=0
        while st<mx:
            anye=0
            for aid in s._aord:
                try:
                    if s.actors[aid].proc(s.log): anye=1
                except RuntimeError as e: s.log.append(f"\n  ERR: {e}"); raise
            st+=1
            if not anye: s.log.append(f"\nHalted at step {st}."); break
        else: s.log.append("\nMax steps reached.")
    def pl(s):
        for l in s.log: print(l)

def run(code,mx=500):
    toks=lex(code); ast=Prs(toks,code).parse(); rt=DR(ast,code)
    en=None
    for n in ("App","Main"):
        if n in ast: en=n; break
    if en is None:
        for nm in ast: rt.inst(nm)
        for aid,a in rt.actors.items():
            if a.d.bs: a.mb.append((list(a.d.bs.keys())[0],[]))
    else:
        eid=rt.inst(en); ea=rt.actors[eid]
        if ea.d.bs: ea.mb.append((list(ea.d.bs.keys())[0],[]))
    rt.run(mx); rt.pl(); return rt

if __name__=="__main__":
    if len(sys.argv)<2: print("Usage: python dython.py <file.dy>"); sys.exit(1)
    with open(sys.argv[1],'r') as f: run(f.read())
