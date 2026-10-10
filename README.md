# SmartLint — Mini Compiler & Static Code Analyzer

A compiler pipeline built in Python using **PLY (Python Lex-Yacc)** and **Streamlit**. SmartLint takes a Python-like source language, runs it through five stages — lexing, parsing, semantic analysis, TAC generation, and optimization — and displays everything in an interactive web dashboard.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Supported Language](#supported-language)
- [Pipeline Stages](#pipeline-stages)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Running the App](#running-the-app)
- [Examples](#examples)
- [Known Limitations](#known-limitations)

---

## Overview

SmartLint was built as an educational mini-compiler to demonstrate the full compilation pipeline from raw source text to optimized intermediate code. It does **not** execute the submitted source — all analysis is static.

The supported language is a strict subset of Python 3 syntax, covering assignments, arithmetic, comparisons, logical expressions, compound assignments, and print statements.

---

## Project Structure

```
SmartLint/
├── compiler/
│   ├── __init__.py
│   ├── lexer.py          # PLY-based lexer — tokenises source text
│   ├── parser.py         # PLY-based LALR(1) parser — builds AST
│   ├── semantic.py       # Type inference, undefined-variable detection, etc.
│   ├── tac.py            # Three-Address Code (TAC) generator
│   └── optimizer.py      # Multi-pass TAC optimizer
├── tests/
│   ├── test_lexer.py     # 36 lexer tests
│   ├── test_parser.py    # 47 parser tests
│   ├── test_semantic.py  # 43 semantic tests
│   ├── test_tac.py       # 31 TAC generation tests
│   ├── test_optimizer.py # 47 optimizer tests
│   └── test_endtoend.py  # 38 end-to-end pipeline tests
├── app.py                # Streamlit dashboard
├── requirements.txt
└── README.md
```

---

## Supported Language

### Data Types

| Type    | Examples                  |
|---------|---------------------------|
| `int`   | `0`, `42`, `-7`           |
| `float` | `3.14`, `0.5`, `-1.0`     |
| `str`   | `"hello"`, `'world'`      |
| `bool`  | `True`, `False`           |

### Operators

| Category        | Operators                              |
|-----------------|----------------------------------------|
| Arithmetic      | `+`  `-`  `*`  `/`  `//`  `%`  `**`  |
| Unary           | `-x`  `+x`                            |
| Comparison      | `==`  `!=`  `<`  `<=`  `>`  `>=`      |
| Logical         | `and`  `or`  `not`                     |
| Assignment      | `=`                                    |
| Compound assign | `+=`  `-=`  `*=`  `/=`  `//=`  `%=`  `**=` |

### Operator Precedence (low → high)

```
or
and
not
== != < <= > >=
+ -
* / // %
** (right-associative)
unary + -   (below ** so that -2**2 == -(2**2) == -4)
( )
```

### Grammar (simplified)

```
program     := statement*
statement   := NAME = expression
             | NAME OP= expression      (OP = + - * / // % **)
             | print ( expression )
expression  := logical_or
logical_or  := logical_and ( or  logical_and )*
logical_and := logical_not ( and logical_not )*
logical_not := not logical_not | comparison
comparison  := arithmetic CMP_OP arithmetic  (non-chaining)
arithmetic  := term ( ( + | - ) term )*
term        := factor ( ( * | / | // | % ) factor )*
factor      := unary ** factor | unary          (right-assoc)
unary       := ( - | + ) unary | primary
primary     := NUMBER | STRING | TRUE | FALSE | NAME | ( expression )
```

### Semantic Rules

- Variables must be assigned before they are used.
- `bool` is **not** numeric — arithmetic on boolean operands is rejected.
- `str` only supports `+` (concatenation of two strings).
- `/` always returns `float`; `//` returns `int` when both operands are `int`.
- Division, floor-division, and modulo by the literal `0` are static errors.
- Comparisons between incompatible types (e.g., `"str" > 5`) are rejected.
- Chained comparisons (`1 < x < 10`) are not supported and produce a syntax error.
- Reassigning a variable to a different type emits a warning (configurable).

---

## Pipeline Stages

```
Source Code
    ↓  Lexer          → tokens + lexical diagnostics
    ↓  Parser         → AST   + syntax diagnostics
    ↓  Semantic       → types + semantic diagnostics
    ↓  TAC generator  → Three-Address Code
    ↓  Optimizer      → Optimized TAC
```

### Lexer (`compiler/lexer.py`)

- Recognises all operators including multi-character ones (`**`, `//`, `**=`, `//=`).
- Longer patterns take priority over shorter ones to prevent mis-tokenisation.
- Tracks line and column for every token.
- Reports structured errors for invalid characters and unterminated strings.

### Parser (`compiler/parser.py`)

- LALR(1) parser built with PLY.
- Full operator precedence and associativity enforced through the grammar.
- `write_tables=False` — no stale `parsetab.py` on disk.
- Structured syntax errors with `"category": "SYNTAX"`.
- AST node types: `assign`, `compound`, `print`, `binary`, `compare`, `logical_and`, `logical_or`, `logical_not`, `unary`, `number`, `string`, `boolean`, `name`.

### Semantic Analyzer (`compiler/semantic.py`)

- Tracks a symbol table of `{name → {type, line}}`.
- Infers types for all expression forms.
- Reports division/modulo/floor-division by literal zero.
- Validates compound assignments (variable must exist first).
- All diagnostics carry `severity`, `category`, `message`, `line`, `column`.

### TAC Generator (`compiler/tac.py`)

- Generates straight-line Three-Address Code with temporaries `t1`, `t2`, …
- Compound `x += e` expands to `t1 = x + e; x = t1`.
- Unary `+` produces no instruction (no-op).
- Unary `-` on a numeric literal produces a single instruction `t1 = -5`.

### Optimizer (`compiler/optimizer.py`)

Multi-pass (until stable, max 20 iterations) with these passes:

1. **Constant folding** — `t1 = 2 + 3` → `t1 = 5`
2. **Constant propagation** — replace a known-constant variable with its value
3. **Copy propagation** — track variable-to-variable copies
4. **Algebraic simplification** — `x * 0 → 0`, `x ** 1 → x`, `x + 0 → x`, etc.
5. **Comparison folding** — `5 > 3` → `True`
6. **Boolean/logical folding** — `True and False` → `False`
7. **String concatenation** — `"hello" + " world"` → `"hello world"`
8. **Unary minus folding** — `-(-5)` folded when operand becomes a constant
9. **Division-by-zero safety** — `/0`, `//0`, `%0` are never folded
10. **Exponent safety** — exponents > 1000 or `0**negative` are never folded

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A virtual environment (recommended)

### Install Dependencies

```powershell
# Create and activate virtual environment (Windows)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

`requirements.txt`:
```
ply
streamlit
pandas
pytest
```

---

## Running Tests

```powershell
# Activate venv first
.venv\Scripts\activate

# Run all 230 tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_optimizer.py -v

# Run with short traceback on failures
python -m pytest tests/ --tb=short
```

**Test counts:**

| File | Tests |
|------|-------|
| `test_lexer.py` | 36 |
| `test_parser.py` | 47 |
| `test_semantic.py` | 43 |
| `test_tac.py` | 31 |
| `test_optimizer.py` | 47 |
| `test_endtoend.py` | 38 |
| **Total** | **230** |

---

## Running the App

```powershell
.venv\Scripts\activate
streamlit run app.py
```

The app opens at `http://localhost:8501`. Use the sidebar to:
- Load one of **8 built-in example programs**.
- Toggle token display, AST raw view, and type-change warnings.
- Browse the language reference panel.

### Dashboard Tabs

| Tab | Shows |
|-----|-------|
| 🩺 Diagnostics | Lexical, syntax, and semantic errors/warnings |
| 🔤 Tokens | Token table with type, value, line, column |
| 🌳 Syntax Tree | Indented, human-readable AST |
| 📚 Symbol Table | Variables, inferred types, definition lines |
| ⚙️ TAC | Original Three-Address Code |
| 🚀 Optimized TAC | Post-optimization instructions + savings count |

---

## Examples

### Valid program

```python
x = 10
y = 3
z = x ** 2 + y * 4
print(z)
result = (x > y) and (z != 0)
print(result)
```

**Optimized TAC:**
```
x = 10
y = 3
t1 = 100
t2 = 12
z = 112
print 112
t3 = True
t4 = True
result = True
print True
```

### Operator precedence

```python
x = -2 ** 2      # -4  (unary lower than **)
y = (-2) ** 2    # 4   (grouped)
z = 2 ** 3 ** 2  # 512 (right-assoc: 2**(3**2))
```

### Errors detected

```python
x = 10 / 0       # ERROR: Division by zero
x = "hi" - 2     # ERROR: Operator '-' cannot be applied to str and int
x += 5            # ERROR: Variable 'x' is used before it is defined
x = True + 1      # ERROR: Operator '+' cannot be applied to bool operands
```

---

## Known Limitations

- No control flow — `if`, `else`, `while`, `for` are not supported.
- No function definitions — only the built-in `print()` call is recognised.
- Chained comparisons (`1 < x < 10`) produce a syntax error by design.
- Division by a variable whose value happens to be zero is not detected (would need data-flow analysis).
- No list, dict, or tuple types — only `int`, `float`, `str`, `bool`.
- The optimizer works on straight-line code only; no control-flow-aware passes.

---

## License

MIT License — see [LICENSE](LICENSE).
