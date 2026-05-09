import re

class Tk:
    def __init__(s, t, v, l=0): s.t, s.v, s.l = t, v, l
    def __repr__(s): return f"Tk({s.t},{s.v!r})"

def lx(c):
    ts = [
        ("C",   r"#[^\n]*"),
        ("K",   r"\b(actor|behav|var|new|iso|val|ref|print)\b"),
        ("I",   r"[a-zA-Z_]\w*"),
        ("BNG", r"!"),
        ("CLN", r":"),
        ("EQ",  r"="),
        ("LP",  r"\("),
        ("RP",  r"\)"),
        ("CMA", r","),
        ("STR", r'"[^"]*"'),
        ("NUM", r"\d+"),
        ("NL",  r"\n"),
        ("WS",  r"[ \t]+"),
    ]
    r_ = "|".join(f"(?P<{a}>{b})" for a, b in ts)
    toks = []
    ln = 1
    for m in re.finditer(r_, c):
        k = m.lastgroup
        v = m.group()
        if k == "NL": ln += 1; continue
        if k in ("WS", "C"): continue
        toks.append(Tk(k, v, ln))
    toks.append(Tk("EOF", "", ln))
    return toks

class AD:
    def __init__(s, n, bs, sv): s.n, s.bs, s.sv = n, bs, sv

class BD:
    def __init__(s, n, ps, b): s.n, s.ps, s.b = n, ps, b

class Asgn:
    def __init__(s, vn, c, val): s.vn, s.c, s.val = vn, c, val

class NewA:
    def __init__(s, vn, at): s.vn, s.at = vn, at

class Send:
    def __init__(s, t, bn, a): s.t, s.bn, s.a = t, bn, a

class Prt:
    def __init__(s, e): s.e = e

class Prs:
    def __init__(s, toks): s.tk = toks; s.p = 0
    def cur(s): return s.tk[s.p]
    def mt(s, t=None, v=None):
        c = s.cur()
        if t and c.t != t: return 0
        if v and c.v != v: return 0
        return 1
    def eat(s, t=None, v=None):
        c = s.cur()
        if t and c.t != t: raise SyntaxError(f"L{c.l}: exp {t}, got {c}")
        if v and c.v != v: raise SyntaxError(f"L{c.l}: exp {v!r}, got {c}")
        s.p += 1
        return c
    def parse(s):
        a = {}
        while not s.mt("EOF"):
            ac = s._actor(); a[ac.n] = ac
        return a
    def _actor(s):
        s.eat("K", "actor"); n = s.eat("I").v
        sv = []; bs = {}
        while not s.mt("EOF") and not s.mt("K", "actor"):
            if s.mt("K", "var"): sv.append(s._sv())
            elif s.mt("K", "behav"): b = s._behav(); bs[b.n] = b
            else: break
        return AD(n, bs, sv)
    def _sv(s):
        s.eat("K", "var"); vn = s.eat("I").v
        s.eat("CLN"); c = s.eat("K").v; s.eat("EQ"); val = s.eat("STR").v
        return (vn, c, val)
    def _behav(s):
        s.eat("K", "behav"); n = s.eat("I").v; ps = s._params(); bd = []
        while not s.mt("EOF") and not (s.mt("K") and s.cur().v in ("behav", "actor")):
            if s.mt("K", "var"): bd.append(s._stmt_var())
            elif s.mt("K", "new"): bd.append(s._stmt_new())
            elif s.mt("K", "print"): bd.append(s._stmt_print())
            elif s.mt("I"): bd.append(s._stmt_send())
            else: break
        return BD(n, ps, bd)
    def _params(s):
        ps = []
        if s.mt("LP"):
            s.eat("LP")
            while not s.mt("RP"):
                pn = s.eat("I").v; pc = "ref"
                if s.mt("CLN"): s.eat("CLN"); pc = s.eat("K").v
                ps.append((pn, pc))
                if s.mt("CMA"): s.eat("CMA")
            s.eat("RP")
        elif s.mt("I"):
            pn = s.eat("I").v; pc = "ref"
            if s.mt("CLN"): s.eat("CLN"); pc = s.eat("K").v
            ps.append((pn, pc))
            while s.mt("CMA"):
                s.eat("CMA"); pn = s.eat("I").v; pc = "ref"
                if s.mt("CLN"): s.eat("CLN"); pc = s.eat("K").v
                ps.append((pn, pc))
        return ps
    def _stmt_var(s):
        s.eat("K", "var"); vn = s.eat("I").v
        s.eat("CLN"); c = s.eat("K").v; s.eat("EQ"); val = s.eat("STR").v
        return Asgn(vn, c, val)
    def _stmt_new(s):
        s.eat("K", "new"); vn = s.eat("I").v; s.eat("EQ"); at = s.eat("I").v
        return NewA(vn, at)
    def _stmt_print(s):
        s.eat("K", "print"); e = s.eat("I").v; return Prt(e)
    def _stmt_send(s):
        t = s.eat("I").v; s.eat("BNG"); bn = s.eat("I").v; s.eat("LP"); args = []
        while not s.mt("RP"):
            args.append(s.eat("I").v)
            if s.mt("CMA"): s.eat("CMA")
        s.eat("RP")
        return Send(t, bn, args)

class Obj:
    _id = 0
    def __init__(s, v, c):
        Obj._id += 1; s.id = Obj._id; s.v = v; s.c = c

class AR:
    def __init__(s, aid, an):
        Obj._id += 1; s.id = Obj._id; s.aid = aid; s.an = an
        s.c = "ref"; s.v = f"<Actor:{an}#{aid}>"

class GC:
    def __init__(s, an, aid):
        s.an = an; s.aid = aid; s.h = {}; s.out = set(); s.ep = 0
    def alloc(s, v, c):
        o = Obj(v, c); s.h[o.id] = o; return o
    def alloc_ar(s, aid, an):
        r = AR(aid, an); s.h[r.id] = r; return r
    def send_proto(s, o):
        if isinstance(o, AR): return o
        if o.c == "iso":
            if o.id in s.h: del s.h[o.id]
            return o
        elif o.c == "val":
            s.out.add(o.id); return o
        elif o.c == "ref":
            raise RuntimeError(f"Data race! ref obj {o.id} '{o.v}' across actors")
    def recv_proto(s, o):
        s.h[o.id] = o
    def ms(s, roots):
        s.ep += 1; reach = set()
        for rid in roots:
            if rid in s.h: reach.add(rid)
        reach.update(s.out)
        to_del = [oid for oid in s.h if oid not in reach]
        swept = []
        for oid in to_del:
            o = s.h[oid]; swept.append((oid, o.v, o.c)); del s.h[oid]
        return swept

class AI:
    def __init__(s, d, aid):
        s.d = d; s.id = aid; s.vars = {}; s.gc = GC(d.n, aid); s.mb = []
    def proc(s, rt, log):
        if not s.mb: return 0
        bn, binds = s.mb.pop(0)
        log.append(f"\n{'─'*55}")
        log.append(f"Actor[{s.id}] ({s.d.n}) > {bn}")
        bh = s.d.bs[bn]
        for pn, o in binds:
            s.gc.recv_proto(o); s.vars[pn] = o.id
            log.append(f"  Param '{pn}' ({o.c}) = \"{o.v}\" [obj {o.id}]")
        for st in bh.b: s._exec(st, rt, log)
        log.append(f"  Orca GC sweep for Actor[{s.id}] ({s.d.n})...")
        roots = list(s.vars.values())
        swept = s.gc.ms(roots)
        for oid, v, c in swept:
            log.append(f"     Swept {c} obj {oid}: '{v}'")
        log.append(f"  Heap: {len(s.gc.h)} | OutRefs: {len(s.gc.out)}")
        return 1
    def _exec(s, st, rt, log):
        if isinstance(st, Asgn):
            o = s.gc.alloc(st.val, st.c); s.vars[st.vn] = o.id; rt.ghm[o.id] = o
            log.append(f"  var {st.vn}: {st.c} = {st.val} [obj {o.id}]")
        elif isinstance(st, NewA):
            nid = rt.inst(st.at, quiet=1)
            r = s.gc.alloc_ar(nid, st.at); s.vars[st.vn] = r.id
            rt.ghm[r.id] = r; rt.arm[r.id] = nid
            log.append(f"  new {st.vn} = {st.at} (aid={nid}, rid={r.id})")
        elif isinstance(st, Prt):
            oid = s.vars.get(st.e)
            if oid is None: log.append(f"  PRINT '{st.e}': not accessible (iso transferred?)")
            else:
                o = rt.ghm.get(oid)
                if o: log.append(f"  PRINT: {o.v}")
                else: log.append(f"  PRINT '{st.e}': GC'd")
        elif isinstance(st, Send): s._send(st, rt, log)
    def _send(s, st, rt, log):
        toid = s.vars.get(st.t)
        if toid is None: log.append(f"  Send: target '{st.t}' not found"); return
        to = rt.ghm.get(toid)
        if not isinstance(to, AR): log.append(f"  Send: '{st.t}' not an Actor"); return
        ta = rt.actors[to.aid]; binds = []
        for an in st.a:
            oid = s.vars.get(an)
            if oid is None: log.append(f"  Send: arg '{an}' not accessible"); return
            o = rt.ghm.get(oid)
            if o is None: log.append(f"  Send: arg '{an}' GC'd"); return
            binds.append(o)
        for o in binds:
            try:
                s.gc.send_proto(o)
                log.append(f"  GC: sending {o.c} obj {o.id} ('{str(o.v)[:25]}')")
                if not isinstance(o, AR) and o.c == "iso":
                    for vn, vid in list(s.vars.items()):
                        if vid == o.id: del s.vars[vn]; log.append(f"     Var '{vn}' revoked (iso)")
            except RuntimeError as e: log.append(f"  {e}"); return
        tb = ta.d.bs.get(st.bn); named = []
        for i, o in enumerate(binds):
            if tb and i < len(tb.ps): named.append((tb.ps[i][0], o))
            else: named.append((f"arg{i}", o))
        ta.mb.append((st.bn, named))
        log.append(f"  '{st.bn}' -> Actor[{to.aid}] ({to.an})")

class DR:
    def __init__(s, ads):
        s.ad = ads; s.actors = {}; s.ghm = {}; s.arm = {}; s.nid = 1; s.log = []
    def inst(s, an, quiet=0):
        d = s.ad[an]; ai = AI(d, s.nid); s.actors[s.nid] = ai; aid = s.nid; s.nid += 1
        if not quiet: s.log.append(f"Instantiated Actor: {an} (id={aid})")
        else: s.log.append(f"  (new) Actor: {an} (id={aid})")
        for vn, c, val in d.sv:
            o = ai.gc.alloc(val, c); ai.vars[vn] = o.id; s.ghm[o.id] = o
        return aid
    def run(s, mx=50):
        s.log.append("\n" + "="*55)
        s.log.append("  Dython Orca GC Runtime -- Start")
        s.log.append("="*55)
        st = 0
        while st < mx:
            anyexec = 0
            for aid in sorted(s.actors.keys()):
                if s.actors[aid].proc(s, s.log): anyexec = 1
            st += 1
            if not anyexec:
                s.log.append(f"\nAll messages processed. Halted at step {st}."); break
        else: s.log.append("\nMax steps reached, halting.")
    def pl(s):
        for l in s.log: print(l)

def run(code, mx=50):
    toks = lx(code); ast = Prs(toks).parse(); rt = DR(ast)
    en = None
    for n in ("App", "Main"):
        if n in ast: en = n; break
    if en is None:
        for nm in ast: rt.inst(nm)
        for aid, a in rt.actors.items():
            if a.d.bs: fb = list(a.d.bs.keys())[0]; a.mb.append((fb, []))
    else:
        eid = rt.inst(en); ea = rt.actors[eid]
        if ea.d.bs: fb = list(ea.d.bs.keys())[0]; ea.mb.append((fb, []))
    rt.run(mx); rt.pl()
    return rt
