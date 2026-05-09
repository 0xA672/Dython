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
- **Orca GC protocol** – each actor has its own local heap and garbage collector. When an object is sent, the sender applies a `send_proto()` protocol; the receiver applies `recv_proto()`. The protocol enforces safety and tracks outgoing references.
- **Per‑actor mark‑and‑sweep GC** – runs after every behaviour execution, cleaning up objects no longer reachable from local variables.
- **Instantiation & dynamic actor creation** – `new ActorName` creates fresh actors at runtime.
- **Simple syntax** – easily readable, with keywords like `actor`, `behav`, `var`, `new`, `print`.

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
var mutable: ref = "I can change"
var payload: iso = "I'll be moved"
```
- Variables must be declared inside actors or behaviours using `var name : capability = "string value"`.
- Only string literals are supported for object values in the current implementation.

### Message Passing
```dython
consumer ! receive(payload)
```
- `target ! behaviour_name(arg1, arg2, ...)` sends an asynchronous message.
- The sender applies the Orca *send protocol* to each argument, which enforces the capability rules.

### Actor Creation
```dython
new worker = Worker
```
- Creates a new actor of type `Worker` and binds it to the variable `worker` as an actor reference.

### The `print` Statement
```dython
print variable_name
```
- Prints the value of a local variable (or indicates if it’s been GC’d or is inaccessible).

## Orca GC in a Nutshell

Dython’s GC is inspired by the **Orca** protocol:

- Every object lives in the heap of the actor that created it.
- **`iso`**: Only one reference exists. When sent, ownership is *transferred* — the sender forgets the variable. No GC coordination needed.
- **`val`**: Can be freely shared. The sender keeps its reference but marks it as an *outgoing reference* (`out` set). The object is kept alive as long as *any* actor holds a reference to it (via local vars or outgoing refs). This is safe because `val` objects are immutable.
- **`ref`**: Mutable and local only. Attempting to send a `ref` object across actors raises a runtime `Data race!` error and aborts the message.
- After each behaviour runs, a **local GC sweep** collects objects that are no longer reachable from the actor’s local variables *or* its outgoing references.

The result: **no stop‑the‑world**, **no global collector**, and **guaranteed data‑race freedom** — just like the real Orca.

## Running Dython

### Requirements
- Python 3.6+ (only uses the standard library and the `re` module).

### Usage
The whole runtime is provided in `dython.py`. You can call the `run()` function with source code:

```python
from dython import run

source = """
actor Hello
    behav world()
        print msg

actor App
    behav main()
        var msg: val = "Hello from Dython!"
        new h = Hello
        h ! world(msg)
"""
run(source)
```

If no `App` or `Main` actor is defined, the runtime instantiates all top‑level actors and invokes their first behaviour (if any).

### Included Tests

Execute the file directly to see five demonstrations:
```bash
python dython.py
```
They illustrate:
1. `iso` ownership transfer
2. `val` shared immutable references
3. `ref` cross‑actor protection (data race prevention)
4. Full actor creation and communication
5. Local GC reclaiming unreachable objects

You’ll see detailed logs of message sends, GC sweeps, and actor state.

## Implementation Overview

| Module / Class      | Purpose |
|---------------------|---------|
| `lx()`             | Lexer – tokenises source code using regex. |
| `Prs`              | Recursive‑descent parser – builds an AST of actors, behaviours, statements. |
| `AD`, `BD`, `Asgn`, `NewA`, `Send`, `Prt` | AST node classes. |
| `Obj`, `AR`        | Runtime representations of objects and actor references. |
| `GC`               | Per‑actor garbage collector implementing the Orca protocol and mark‑sweep. |
| `AI`               | Actor instance – runs behaviours, stores local variables and heap. |
| `DR`               | Dython Runtime – instantiates actors, manages the global object map, and runs the event loop. |
| `run()`            | Convenience function: lex, parse, instantiate, run, and print the log. |

## Limitations

- Only string literals are supported as values.
- No arithmetic, conditionals, loops, or user‑defined capabilities.
- Actors are single‑threaded and run cooperatively (one behaviour at a time, in a fixed order).
- The parser is permissive but fragile; error messages are basic.
- `ref` parameters in behaviours are not deeply checked for safety – the model trusts that actors do not expose them externally.

Dython is a **teaching tool**, not a production language. It crystallises the core ideas of the Orca GC into a runnable, inspectable system.

---

*Dython was created to make the principles of Pony’s garbage collector approachable and fun. Fork it, hack it, and learn from it!*
