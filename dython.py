import re
from collections import deque
import sys

class Tk:
    def __init__(s, t, v, l=0): s.t, s.v, s.l = t, v, l
    def __repr__(s): return f"Tk({s.t},{s.v!r})"

_LEX_TS = [
    ("C",   r"#[^\n]*"),
    ("K",   r"\b(actor|behav|var|new|iso|val|ref|print|if|else|while)\b"),
    ("EQEQ", r"=="), ("NEQ", r"!="), ("LE", r"<="), ("GE", r">="),
    ("BNG", r"!"), ("EQ", r"="), ("LT", r"<"), ("GT", r">"),
    ("ADD", r"\+"), ("SUB", r"-"), ("MUL", r"\*"), ("DIV", r"/"),
    ("I",   r"[a-zA-Z_]\w*"),
    ("LP",  r"\("), ("RP", r"\)"), ("CMA", r","), ("CLN", r":"),
    ("STR", r'"[^"]*"'),
    ("N",   r"\d+"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("NL",  r"\n"),
    ("WS",  r"[ \t]+"),
    ("ERR", r"."),
]
_LEX_RE = re.compile("|".join(f"(?P<{a}>{b})" for a, b in _LEX_TS))

def lx(c):
    toks, ln = [], 1
    for m in _LEX_RE.finditer(c):
        k, v = m.lastgroup, m.group()
        if k == "ERR":
            raise SyntaxError(f"L{ln}: illegal character '{v}'")
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
    def __init__(s, vn, c, val, line=0): s.vn, s.c, s.val, s.line = vn, c, val, line

class NewA:
    def __init__(s, vn, at, line=0): s.vn, s.at, s.line = vn, at, line

class Send:
    def __init__(s, t, bn, a, line=0): s.t, s.bn, s.a, s.line = t, bn, a, line

class Prt:
    def __init__(s, e, line=0): s.e, s.line = e, line

class If:
    def __init__(s, cond, body, else_body, line=0): s.cond, s.body, s.else_body, s.line = cond, body, else_body, line

class While:
    def __init__(s, cond, body, line=0): s.cond, s.body, s.line = cond, body, line

class Lit:
    def __init__(s, v, typ, line=0): s.v, s.typ, s.line = v, typ, line

class Var:
    def __init__(s, name, line=0): s.name, s.line = name, line

class Bop:
    def __init__(s, op, left, right, line=0): s.op, s.left, s.right, s.line = op, left, right, line

class Prs:
    def __init__(s, toks, src=""): s.tk, s.p, s.src = toks, 0, src.split("\n") if src else []

    def cur(s): return s.tk[s.p]

    def mt(s, t=None, v=None):
        c = s.cur()
        if t and c.t != t: return False
        if v and c.v != v: return False
        return True

    def eat(s, t=None, v=None):
        c = s.cur()
        if t and c.t != t:
            exp = f"token type '{t}'"
            if v: exp = f"'{v}'"
            s._err(f"expected {exp}, got {c}")
        if v and c.v != v:
            s._err(f"expected '{v}', got '{c.v}'")
        s.p += 1
        return c

    def _err(s, msg):
        c = s.cur()
        line = c.l
        hint = ""
        if 1 <= line <= len(s.src):
            sl = s.src[line-1]
            indent = len(sl) - len(sl.lstrip())
            hint = "\n  " + sl + "\n  " + " " * indent + "^"
        raise SyntaxError(f"L{line}: {msg}{hint}")

    def parse(s):
        a = {}
        while not s.mt("EOF"):
            ac = s._actor(); a[ac.n] = ac
        return a

    def _actor(s):
        s.eat("K", "actor"); n = s.eat("I").v
        sv, bs = [], {}
        while not s.mt("EOF") and not s.mt("K", "actor"):
            if s.mt("K", "var"): sv.append(s._sv())
            elif s.mt("K", "behav"): b = s._behav(); bs[b.n] = b
            else: break
        return AD(n, bs, sv)

    def _sv(s):
        s.eat("K", "var"); vn = s.eat("I").v
        s.eat("CLN"); c = s.eat("K").v
        s.eat("EQ"); val = s.expr()
        s._chk_no_var(val)
        return (vn, c, val)

    def _behav(s):
        s.eat("K", "behav"); n = s.eat("I").v
        ps = s._params(); bd = []
        while not s.mt("EOF") and not (s.mt("K") and s.cur().v in ("behav", "actor")):
            if s.mt("K", "var"): bd.append(s._stmt_var())
            elif s.mt("K", "new"): bd.append(s._stmt_new())
            elif s.mt("K", "print"): bd.append(s._stmt_print())
            elif s.mt("K", "if"): bd.append(s._stmt_if())
            elif s.mt("K", "while"): bd.append(s._stmt_while())
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
        else:
            s._err("expected '(' after behavior name")
        return ps

    def _stmt_var(s):
        line = s.cur().l
        s.eat("K", "var"); vn = s.eat("I").v
        s.eat("CLN"); c = s.eat("K").v
        s.eat("EQ"); val = s.expr()
        return Asgn(vn, c, val, line)

    def _stmt_new(s):
        line = s.cur().l
        s.eat("K", "new"); vn = s.eat("I").v
        s.eat("EQ"); at = s.eat("I").v
        return NewA(vn, at, line)

    def _stmt_print(s):
        line = s.cur().l
        s.eat("K", "print"); e = s.expr()
        return Prt(e, line)

    def _stmt_send(s):
        line = s.cur().l
        t = s.eat("I").v; s.eat("BNG"); bn = s.eat("I").v
        s.eat("LP"); args = []
        while not s.mt("RP"):
            args.append(s.expr())
            if s.mt("CMA"): s.eat("CMA")
        s.eat("RP")
        return Send(t, bn, args, line)

    def _stmt_if(s):
        line = s.cur().l
        s.eat("K", "if")
        cond = s.expr()
        body = s._block()
        else_body = []
        if s.mt("K", "else"):
            s.eat("K", "else")
            else_body = s._block()
        return If(cond, body, else_body, line)

    def _stmt_while(s):
        line = s.cur().l
        s.eat("K", "while")
        cond = s.expr()
        body = s._block()
        return While(cond, body, line)

    def _block(s):
        s.eat("LBRACE")
        stmts = []
        while not s.mt("RBRACE") and not s.mt("EOF"):
            if s.mt("K", "var"): stmts.append(s._stmt_var())
            elif s.mt("K", "new"): stmts.append(s._stmt_new())
            elif s.mt("K", "print"): stmts.append(s._stmt_print())
            elif s.mt("K", "if"): stmts.append(s._stmt_if())
            elif s.mt("K", "while"): stmts.append(s._stmt_while())
            elif s.mt("I"): stmts.append(s._stmt_send())
            else: break
        s.eat("RBRACE")
        return stmts

    def expr(s): return s._comp()

    def _comp(s):
        left = s._sum()
        while s.mt("EQEQ") or s.mt("NEQ") or s.mt("LT") or s.mt("GT") or s.mt("LE") or s.mt("GE"):
            op = s.cur().t; s.eat(op); right = s._sum()
            left = Bop(op, left, right, s.cur().l)
        return left

    def _sum(s):
        left = s._term()
        while s.mt("ADD") or s.mt("SUB"):
            op = s.cur().t; s.eat(op); right = s._term()
            left = Bop(op, left, right, s.cur().l)
        return left

    def _term(s):
        left = s._atom()
        while s.mt("MUL") or s.mt("DIV"):
            op = s.cur().t; s.eat(op); right = s._atom()
            left = Bop(op, left, right, s.cur().l)
        return left

    def _atom(s):
        if s.mt("N"): t = s.eat("N"); return Lit(int(t.v), 'int', t.l)
        elif s.mt("STR"): t = s.eat("STR"); return Lit(t.v[1:-1], 'str', t.l)
        elif s.mt("I"): t = s.eat("I"); return Var(t.v, t.l)
        elif s.mt("LP"): s.eat("LP"); e = s.expr(); s.eat("RP"); return e
        else:
            s._err(f"unexpected token {s.cur()}")

    def _chk_no_var(s, expr):
        def has_var(e):
            if isinstance(e, Var): return True
            if isinstance(e, Bop): return has_var(e.left) or has_var(e.right)
            return False
        if has_var(expr):
            s._err("actor state var init cannot reference variables")

class Obj:
    def __init__(s, v, c, oid):
        s.id = oid; s.v = v; s.c = c

class AR:
    def __init__(s, aid, an, oid):
        s.id = oid; s.aid = aid; s.an = an
        s.c = "ref"; s.v = f"<Actor:{an}#{aid}>"

class GC:
    def __init__(s, an, aid, rt):
        s.an, s.aid, s.h, s.rt = an, aid, {}, rt

    def alloc(s, v, c):
        oid = s.rt._fresh_id()
        o = Obj(v, c, oid)
        s.h[o.id] = o; s.rt._inc_ref(o.id)
        return o

    def alloc_ar(s, aid, an):
        oid = s.rt._fresh_id()
        r = AR(aid, an, oid)
        s.h[r.id] = r; s.rt._inc_ref(r.id)
        return r

    def send_proto(s, o):
        if isinstance(o, AR): return o
        if o.c == "iso":
            if o.id in s.h: del s.h[o.id]; s.rt._dec_ref(o.id)
            return o
        elif o.c == "val":
            return o
        elif o.c == "ref":
            raise RuntimeError(f"Data race! ref obj {o.id} '{o.v}' cannot be sent")
        raise RuntimeError(f"unknown capability {o.c} in send")

    def recv_proto(s, o):
        s.h[o.id] = o; s.rt._inc_ref(o.id); s.rt.ghm[o.id] = o

    def ms(s, roots):
        reach = set(roots)
        swept = []
        for oid in list(s.h.keys()):
            if oid not in reach:
                swept.append((oid, s.h[oid].v, s.h[oid].c))
                del s.h[oid]; s.rt._dec_ref(oid)
        return swept

class AI:
    MAX_WHILE_ITERS = 10000

    def __init__(s, d, aid, rt):
        s.d, s.id, s.rt, s.vars, s.gc, s.mb = d, aid, rt, {}, GC(d.n, aid, rt), deque()

    def proc(s, log):
        if not s.mb: return 0
        bn, binds = s.mb.popleft()
        log.append(f"\n{'─'*55}")
        log.append(f"Actor[{s.id}] ({s.d.n}) > {bn}")

        if bn not in s.d.bs:
            s._err(f"behavior '{bn}' not found in actor '{s.d.n}'", 0)
        bh = s.d.bs[bn]

        state_vars = {sv[0] for sv in s.d.sv}

        for i, (pn, o) in enumerate(binds):
            if bh and i < len(bh.ps):
                param_cap = bh.ps[i][1]
                if o.c != param_cap:
                    s._err(f"behavior '{bn}' param '{pn}' expects {param_cap}, got {o.c}", 0)
            s.gc.recv_proto(o); s.vars[pn] = o.id
            log.append(f"  Param '{pn}' ({o.c}) = \"{o.v}\" [obj {o.id}]")

        for st in bh.b:
            s._exec(st, log)

        s.vars = {k: v for k, v in s.vars.items() if k in state_vars}
        log.append(f"  Orca GC sweep for Actor[{s.id}] ({s.d.n})...")
        roots = list(s.vars.values())
        swept = s.gc.ms(roots)
        for oid, v, c in swept:
            log.append(f"     Swept {c} obj {oid}: '{v}'")
        log.append(f"  Heap: {len(s.gc.h)} objs")
        return 1

    def _err(s, msg, line):
        src = s.rt.src
        hint = ""
        if src and 1 <= line <= len(src):
            sl = src[line-1]
            indent = len(sl) - len(sl.lstrip())
            hint = "\n  " + sl + "\n  " + " " * indent + "^"
        raise RuntimeError(f"L{line} Actor[{s.id}] '{s.d.n}': {msg}{hint}")

    def _truthy(s, oid):
        o = s.rt.ghm.get(oid)
        if o is None: return False
        val = o.v
        if isinstance(val, bool): return val
        if isinstance(val, int): return val != 0
        if isinstance(val, str): return val != ""
        return True

    def _exec(s, st, log):
        if isinstance(st, Asgn):
            oid = s._eval(st.val)
            o = s.rt.ghm.get(oid)
            if o is None: s._err(f"value object {oid} no longer exists", st.line)
            o.c = st.c
            old_oid = s.vars.get(st.vn)
            if old_oid is not None:
                del s.vars[st.vn]
            if o.c == "iso":
                s._check_iso_alias(oid, st.vn, st.line)
            s.vars[st.vn] = oid
            log.append(f"  var {st.vn}: {o.c} = \"{o.v}\" [obj {oid}]")
        elif isinstance(st, NewA):
            nid = s.rt.inst(st.at, quiet=1)
            r = s.gc.alloc_ar(nid, st.at)
            s.rt.ghm[r.id] = r; s.rt.arm[r.id] = nid
            old_oid = s.vars.get(st.vn)
            if old_oid is not None:
                del s.vars[st.vn]
            s.vars[st.vn] = r.id
            log.append(f"  new {st.vn} = {st.at} (actor_id={nid}, ref_id={r.id})")
        elif isinstance(st, Prt):
            oid = s._eval(st.e)
            o = s.rt.ghm.get(oid)
            if o: log.append(f"  PRINT: {o.v}")
            else: log.append("  PRINT: Object GC'd")
        elif isinstance(st, Send):
            s._send(st, log)
        elif isinstance(st, If):
            oid = s._eval(st.cond)
            if s._truthy(oid):
                for sub in st.body: s._exec(sub, log)
            else:
                for sub in st.else_body: s._exec(sub, log)
        elif isinstance(st, While):
            iters = 0
            while True:
                if iters >= AI.MAX_WHILE_ITERS:
                    s._err(f"while loop exceeded max iterations ({AI.MAX_WHILE_ITERS})", st.line)
                oid = s._eval(st.cond)
                if not s._truthy(oid): break
                for sub in st.body: s._exec(sub, log)
                iters += 1

    def _check_iso_alias(s, oid, new_vn, line):
        for vn, vid in s.vars.items():
            if vid == oid:
                s._err(f"iso object {oid} already held by variable '{vn}', cannot create alias '{new_vn}'", line)

    def _send(s, st, log):
        toid = s.vars.get(st.t)
        if toid is None:
            known = ", ".join(s.vars.keys())
            s._err(f"target '{st.t}' not found. Known vars: {known}", st.line)
        to = s.rt.ghm.get(toid)
        if to is None:
            s._err(f"target actor object {toid} no longer exists", st.line)
        if not isinstance(to, AR):
            s._err(f"'{st.t}' is not an actor (type: {type(to).__name__})", st.line)
        ta = s.rt.actors.get(to.aid)
        if ta is None:
            s._err(f"actor with id {to.aid} not found", st.line)

        arg_oids = []
        for ae in st.a:
            oid = s._eval(ae)
            o = s.rt.ghm.get(oid)
            if o is None: s._err(f"argument object {oid} no longer exists", st.line)
            arg_oids.append((oid, o))

        for oid, o in arg_oids:
            if o.c == "ref":
                s._err(f"cannot send ref object {oid} '{o.v}'", st.line)

        for oid, o in arg_oids:
            s.gc.send_proto(o)
            log.append(f"  GC: sending {o.c} obj {oid} ('{str(o.v)[:25]}')")
            if o.c == "iso":
                to_remove = [vn for vn, vid in s.vars.items() if vid == oid]
                for vn in to_remove:
                    del s.vars[vn]
                    log.append(f"     Var '{vn}' revoked (iso)")

        for oid, o in arg_oids:
            if o.c == "iso":
                for vn, vid in s.vars.items():
                    if vid == oid:
                        s._err(
                            f"iso alias after revocation: '{vn}' still holds obj {oid}",
                            st.line,
                        )

        tb = ta.d.bs.get(st.bn)
        named = []
        for i, (oid, o) in enumerate(arg_oids):
            if tb and i < len(tb.ps):
                named.append((tb.ps[i][0], o))
            else:
                named.append((f"arg{i}", o))
        ta.mb.append((st.bn, named))
        log.append(f"  '{st.bn}' -> Actor[{to.aid}] ({to.an})")

    def _eval(s, expr):
        if isinstance(expr, Lit):
            o = s.gc.alloc(expr.v, "val"); s.rt.ghm[o.id] = o; return o.id
        elif isinstance(expr, Var):
            oid = s.vars.get(expr.name)
            if oid is None:
                known = ", ".join(s.vars.keys())
                s._err(f"variable '{expr.name}' not found. Known vars: {known}", expr.line)
            if s.rt.ghm.get(oid) is None:
                s._err(f"object {oid} associated with '{expr.name}' no longer exists", expr.line)
            return oid
        elif isinstance(expr, Bop):
            left_id = s._eval(expr.left)
            right_id = s._eval(expr.right)
            lo = s.rt.ghm.get(left_id); ro = s.rt.ghm.get(right_id)
            if lo is None or ro is None:
                s._err(f"operand no longer exists", expr.line)
            lv, rv = lo.v, ro.v; op = expr.op
            if isinstance(lv, str) and isinstance(rv, str):
                if op == "ADD":
                    res = lv + rv
                elif op == "EQEQ":
                    res = int(lv == rv)
                elif op == "NEQ":
                    res = int(lv != rv)
                else:
                    s._err(f"unsupported string operator {op}", expr.line)
            elif (isinstance(lv, int) or isinstance(lv, bool)) and (isinstance(rv, int) or isinstance(rv, bool)):
                if op == "ADD": res = lv + rv
                elif op == "SUB": res = lv - rv
                elif op == "MUL": res = lv * rv
                elif op == "DIV":
                    if rv == 0: s._err("division by zero", expr.line)
                    res = lv // rv
                elif op == "EQEQ": res = int(lv == rv)
                elif op == "NEQ":  res = int(lv != rv)
                elif op == "LT":   res = int(lv < rv)
                elif op == "GT":   res = int(lv > rv)
                elif op == "LE":   res = int(lv <= rv)
                elif op == "GE":   res = int(lv >= rv)
                else: s._err(f"unsupported operator {op}", expr.line)
            else:
                s._err(f"type mismatch in {op}: {type(lv).__name__} ({lv}) vs {type(rv).__name__} ({rv})", expr.line)
            o = s.gc.alloc(res, "val"); s.rt.ghm[o.id] = o; return o.id
        else:
            s._err(f"bad expression node {type(expr).__name__}", 0)

class DR:
    def __init__(s, ads, src=None):
        s.ad, s.actors, s.ghm, s.arm, s.nid, s.log = ads, {}, {}, {}, 1, []
        s.refcnt = {}
        s.src = src.split("\n") if src else []
        s._aid_order = []
        s._next_id = 1

    def _fresh_id(s):
        oid = s._next_id
        s._next_id += 1
        return oid

    def _inc_ref(s, oid):
        s.refcnt[oid] = s.refcnt.get(oid, 0) + 1

    def _dec_ref(s, oid):
        if oid in s.refcnt:
            s.refcnt[oid] -= 1
            if s.refcnt[oid] <= 0:
                del s.refcnt[oid]
                if oid in s.ghm:
                    del s.ghm[oid]

    def inst(s, an, quiet=0):
        if an not in s.ad:
            raise RuntimeError(f"actor type '{an}' is not defined")
        d = s.ad[an]
        ai = AI(d, s.nid, s)
        s.actors[s.nid] = ai
        aid = s.nid
        s.nid += 1
        s._aid_order.append(aid)
        if not quiet:
            s.log.append(f"Instantiated Actor: {an} (id={aid})")
        else:
            s.log.append(f"  (new) Actor: {an} (id={aid})")
        for vn, c, val in d.sv:
            oid = ai._eval(val)
            o = s.ghm.get(oid)
            if o is None:
                raise RuntimeError(f"State init object {oid} missing")
            o.c = c
            ai.vars[vn] = oid
        return aid

    def run(s, mx=500):
        s.log.append("\n" + "="*55)
        s.log.append("  Dython Orca GC Runtime -- Start")
        s.log.append("="*55)
        st = 0
        while st < mx:
            anyexec = 0
            for aid in s._aid_order:
                try:
                    if s.actors[aid].proc(s.log):
                        anyexec = 1
                except RuntimeError as e:
                    s.log.append(f"\n  RUNTIME ERROR: {e}")
                    raise
            st += 1
            if not anyexec:
                s.log.append(f"\nAll messages processed. Halted at step {st}.")
                break
        else:
            s.log.append("\nMax steps reached, halting.")

    def pl(s):
        for l in s.log:
            print(l)

def run(code, mx=500):
    toks = lx(code)
    ast = Prs(toks, code).parse()
    rt = DR(ast, code)
    en = None
    for n in ("App", "Main"):
        if n in ast:
            en = n
            break
    if en is None:
        for nm in ast:
            rt.inst(nm)
        for aid, a in rt.actors.items():
            if a.d.bs:
                fb = list(a.d.bs.keys())[0]
                a.mb.append((fb, []))
    else:
        eid = rt.inst(en)
        ea = rt.actors[eid]
        if ea.d.bs:
            fb = list(ea.d.bs.keys())[0]
            ea.mb.append((fb, []))
    rt.run(mx)
    rt.pl()
    return rt

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dython.py <file.dy>")
        sys.exit(1)
    with open(sys.argv[1], 'r') as f:
        code = f.read()
    run(code)
