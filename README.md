# Dython — A Minimal Actor Language with Orca-Inspired GC

Dython is a tiny, self-contained actor‑based programming language interpreter written in Python.  
It demonstrates **Orca‑style garbage collection** combined with **reference capabilities** (`iso`, `val`, `ref`) to ensure data‑race freedom and deterministic memory management across concurrent actors.

> The name “Dython” is a playful blend of *D(istributed)* and *Python* — it’s a toy language that illustrates the ideas behind the [Orca](https://www.doc.ic.ac.uk/~scd/Orca-GC-residency.pdf) garbage collector used in the [Pony](https://www.ponylang.io/) language, but implemented in a few hundred lines of Python.

---

## Features

- **Actor model** – all computation happens inside actors, communicating via asynchronous message passing.
- **Reference capabilities** – every object has one of three capabilities:
  - `iso` – isolated, mutable only by the owning actor, transferred on send (ownership moves).
  - `val` – deeply immutable, can be shared freely, but the original sender keeps a reference (outgoing refs tracked).
  - `ref` – mutable local reference; **cannot** be sent to another actor (would cause data races).
- **Expressions & arithmetic** – integer and string literals, plus basic arithmetic (`+`, `-`, `*`, `/`) and comparisons (`==`, `!=`, `<`, `>`, `<=`, `>=`). Variables can be used in expressions where allowed.
- **Orca GC protocol** – each actor has its own local heap and garbage collector. When an object is sent, the sender applies a `send_proto()` protocol; the receiver applies `recv_proto()`. The protocol enforces safety and tracks outgoing references.
- **Per‑actor mark‑and‑sweep GC** – runs after every behaviour execution, cleaning up objects no longer reachable from local variables. Now with proper global heap map cleanup (no memory leak).
- **Performance optimizations** – compiled regex, `deque` for message queues, O(1) variable lookup for `iso` revocation, and stable actor ordering without per-step sorting.
- **Friendly error messages** – both syntax and runtime errors pinpoint the exact source line with a caret indicator and actor context.
- **Executable `.dy` files** – run `python dython.py program.dy` to execute Dython source files.

## Language Tour

### Actors and Behaviours
```dython
actor Greeter
    behav greet(name: val)
        print name
```

- `actor` defines a new actor class with optional `var`‑declared state.
- `behav` defines a behaviour (message handler). Parameters can have an optional capability (`:val`, `:iso`, `:ref`). Default is `ref`.

### Variables and Capabilities
```dython
var greeting: val = "Hello, Dython!"
var answer: val = 40 + 2
var payload: iso = "I'll be moved"
```
- Actor state variables (declared directly inside an `actor` block) must be initialised with literal‑only expressions (no variable references).
- Behaviour‑local `var` statements can use any expression, including references to other local variables.
- Capabilities: `val` for immutable data, `ref` for local mutable, `iso` for transferable ownership.

### Expressions
```dython
var x: val = 10 + 20 * 3
var y: val = x + 5
print y
```
- Integers and strings are fully supported.
- Arithmetic: `+`, `-`, `*`, `/` (integer division).
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`.
- Parentheses can be used for grouping.

### Message Passing
```dython
consumer ! receive(payload)
calc ! compute(10 + 5, "result")
```
- `target ! behaviour_name(arg1, arg2, ...)` sends an asynchronous message.
- Arguments can be arbitrary expressions, evaluated before sending.
- The sender applies the Orca *send protocol* to each argument, which enforces the capability rules.

### Actor Creation
```dython
new worker = Worker
```
- Creates a new actor of type `Worker` and binds it to the variable `worker` as an actor reference.

### The `print` Statement
```dython
print variable_name
print 1 + 2
```
- Prints the value of any expression. If the object has been GC'd or is otherwise inaccessible, a warning is shown.

## Orca GC in a Nutshell

Dython’s GC is inspired by the **Orca** protocol:

- Every object lives in the heap of the actor that created it.
- **`iso`**: Only one reference exists. When sent, ownership is *transferred* — the sender forgets the variable. No GC coordination needed.
- **`val`**: Can be freely shared. The sender keeps its reference but marks it as an *outgoing reference* (`out` set). The object is kept alive as long as *any* actor holds a reference to it (via local vars or outgoing refs). This is safe because `val` objects are immutable.
- **`ref`**: Mutable and local only. Attempting to send a `ref` object across actors raises a runtime `Data race!` error and aborts the message.
- After each behaviour runs, a **local GC sweep** collects objects that are no longer reachable from the actor’s local variables *or* its outgoing references. Now the global heap map is also properly cleaned, preventing memory leaks.

The result: **no stop‑the‑world**, **no global collector**, and **guaranteed data‑race freedom** — just like the real Orca.

## Running Dython

### Requirements
- Python 3.6+ (only uses the standard library and the `re` module).

### Usage
The whole runtime is provided in `dython.py`. You can call the `run()` function with source code, or execute a `.dy` file directly:

```python
from dython import run

source = """
actor Calc
    behav result()
        var x: val = 10 + 20 * 3
        print x

actor App
    behav main()
        new c = Calc
        c ! result()
"""
run(source)
```

To run a Dython source file:
```bash
python dython.py example.dy
```

If no `App` or `Main` actor is defined, the runtime instantiates all top‑level actors and invokes their first behaviour (if any).

### Included Tests (12 passing)

Execute the file directly to see a suite of demonstrations:
```bash
python dython.py
```
They cover:
1. `iso` ownership transfer
2. `val` shared immutable references
3. `ref` cross‑actor protection (data race prevention)
4. Full actor creation and communication
5. Local GC reclaiming unreachable objects
6. Integer arithmetic and expression evaluation
7–12. Additional edge cases for capabilities and GC behaviour

You’ll see detailed logs of message sends, GC sweeps, and actor state. All tests pass cleanly with the current codebase.

## Implementation Overview

| Module / Class      | Purpose |
|---------------------|---------|
| `lx()`             | Lexer – tokenises source code using a precompiled regex. |
| `Prs`              | Recursive‑descent parser – builds an AST, stores line numbers for precise error reporting. |
| `AD`, `BD`, `Asgn`, `NewA`, `Send`, `Prt`, `Lit`, `Var`, `Bop` | AST nodes – all carry source line information. |
| `Obj`, `AR`        | Runtime objects and actor references. |
| `GC`               | Per‑actor garbage collector – Orca send/recv protocols, mark‑sweep with proper global map cleanup. Uses O(1) variable revocation via reverse mapping. |
| `AI`               | Actor instance – uses `deque` for the message queue, runs behaviours, evaluates expressions. |
| `DR`               | Dython Runtime – instantiates actors, maintains stable insertion order, runs the event loop, and collects source for error display. |
| `run()`            | Convenience API: lex, parse, instantiate, run, and print. |

## Recent Improvements

- **Memory leak fixed**: GC now synchronises `rt.ghm` during sweeps.
- **Performance**: replaced `list` with `deque` for message queues; precompiled the lexer regex; removed per-step actor sorting; `iso` revocation is now O(1).
- **Error reporting**: syntax and runtime errors include the offending source line, a caret pointing to the error position, and the actor identifier.
- **Control flow**: added `if`/`else` and `while` with block syntax `{}`.

## Limitations

- Limited control flow: `if`/`else` and `while` loops work, but no `for`, pattern matching, or loop‑control statements (`break`, `continue`).
- Only integer and string types; no user‑defined classes or arrays.
- Expression evaluation always creates new `val` objects on the fly for intermediate results (no in‑place mutation).
- Actors are single‑threaded and run cooperatively (one behaviour at a time, in a fixed order).
- `ref` parameters in behaviours are not deeply checked for safety – the model trusts that actors do not expose them externally.

Dython is a **teaching tool**, not a production language. It crystallises the core ideas of the Orca GC into a runnable, inspectable system, and continues to evolve as a playground for language design.

---

## License

MIT License

Copyright (c) 2025 0xA672

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
