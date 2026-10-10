# SmartLint — Mini Compiler and Static Code Analyzer
## Project Report

**Course:** Compiler Design  
**Project Title:** SmartLint — Mini Compiler and Static Code Analyzer  
**Technology Stack:** Python 3, PLY (Python Lex-Yacc), Streamlit, pytest  

---

## 1. Introduction

When we were given this project I'll be honest — I thought building a compiler was going to be an overwhelming task. Most of what I knew about compilers came from theory classes: tokens, grammars, parse trees, the usual. Actually sitting down and writing one from scratch is a different experience entirely.

SmartLint is what came out of that process. It's a mini compiler and static code analyzer for a Python-like language. The idea was not to build a full Python interpreter — that would be unrealistic for a semester project — but to pick a meaningful subset of Python syntax and implement the full pipeline from reading raw source text all the way to generating and optimizing intermediate code.

The tool doesn't execute the code you give it. It analyzes it — figures out whether it's valid, what types variables should have, where errors are, and what the simplified intermediate instructions look like. This is closer to what real compilers do during their front-end passes.

---

## 2. What the Project Does

At a high level, you paste some code in a text box, click "Run Analysis," and SmartLint walks it through five stages:

1. **Lexer** — breaks the source into tokens
2. **Parser** — checks the grammar and builds an Abstract Syntax Tree (AST)
3. **Semantic Analyzer** — checks for type errors, undefined variables, division by zero, etc.
4. **TAC Generator** — converts the AST into Three-Address Code (intermediate representation)
5. **Optimizer** — simplifies the TAC using several standard optimization techniques

The results are shown in a tabbed dashboard built with Streamlit. Each tab corresponds to one stage, so you can see exactly what each phase of the compiler produced.

---

## 3. The Language

Probably the most important decision early on was: what exactly should this language support? If you try to support everything, you end up with an incomplete implementation of everything. So I narrowed it down to a fixed, documented set of features.

**Data types supported:**
- Integers (e.g. `42`, `-7`)
- Floating-point numbers (e.g. `3.14`, `0.5`)
- Strings (both `"double"` and `'single'` quoted)
- Booleans (`True`, `False`)

**Operators implemented:**
- All standard arithmetic: `+`, `-`, `*`, `/`, `//` (floor div), `%` (modulo), `**` (exponentiation)
- Unary plus and minus: `+x`, `-x`
- All comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Logical operators: `and`, `or`, `not`
- Simple assignment: `=`
- Compound assignments: `+=`, `-=`, `*=`, `/=`, `//=`, `%=`, `**=`

**What is explicitly NOT supported:**
- `if` / `else` / `elif`
- `while`, `for` loops
- Function definitions
- Lists, dicts, tuples
- Chained comparisons like `1 < x < 10`

Chained comparisons were actually a choice I made deliberately. Python supports them, but implementing them correctly in a grammar without ambiguity is tricky. Rather than silently parsing them wrong, SmartLint just rejects them with a syntax error and a clear message. That felt more honest than letting incorrect behavior slip through.

One rule I was particularly careful about: **booleans are not numeric in this language**. In Python, `True + 1 == 2` because `bool` is a subclass of `int`. SmartLint explicitly rejects that. If you try `True + 1`, you get a semantic error. I think that's the right call for an educational compiler — it teaches cleaner type habits.

---

## 4. Implementation

### 4.1 Lexer

The lexer is built using PLY's `lex` module. PLY lets you define token rules either as simple string patterns or as functions. The key thing I learned here is that **order matters** for multi-character operators.

For example, `**` must be recognized before `*`, `//` before `/`, and `**=` before `**`. In PLY, function-based rules take priority over string rules, and among string rules, longer strings match first. So to handle this correctly, all compound and multi-character operators are implemented as functions:

```python
def t_POW_EQ(t):
    r"\*\*="
    return t

def t_POW(t):
    r"\*\*"
    return t
```

This ensures `**=` is never mis-tokenised as `**` followed by `=`.

The lexer also tracks column numbers. PLY gives you line numbers for free (via `lineno`), but column requires manual calculation — you scan backward from the token's position to find the last newline.

Errors are reported as structured dictionaries:
```python
{
    "severity": "ERROR",
    "category": "LEXICAL",
    "message": "Invalid character '@'",
    "line": 2,
    "column": 5
}
```

### 4.2 Parser

The parser uses PLY's LALR(1) parser generator. The precedence table was the most important thing to get right here. LALR parsers use precedence rules to resolve shift-reduce conflicts, and if you get the table wrong, expressions parse incorrectly without any visible error.

The final precedence table, from lowest to highest:

```python
precedence = (
    ("left",  "OR"),
    ("left",  "AND"),
    ("right", "NOT"),
    ("left",  "EQ", "NE", "LT", "LE", "GT", "GE"),
    ("left",  "PLUS", "MINUS"),
    ("left",  "TIMES", "DIVIDE", "FLOORDIV", "MOD"),
    ("right", "UMINUS", "UPLUS"),
    ("right", "POW"),
)
```

The interesting part here is the placement of `UMINUS` and `UPLUS`. In Python, `-2 ** 2` evaluates to `-4`, not `4`. That's because the unary minus binds *less tightly* than exponentiation. To get this right, unary operators must sit **below** `POW` in the precedence table, not above it. Early versions had this reversed, which produced the wrong result for that case.

Each AST node is a plain Python dictionary. For example:

```python
# Binary operation: 2 + 3
{
    "type": "binary",
    "operator": "+",
    "left":  {"type": "number", "value": 2, "line": 1},
    "right": {"type": "number", "value": 3, "line": 1},
    "line": 1
}
```

Using plain dicts rather than custom classes made it much easier to debug — you can just print any node and immediately read what it contains.

### 4.3 Semantic Analyzer

The semantic analyzer walks the AST and does two things: it infers the type of every expression, and it reports any violations.

The symbol table maps variable names to their inferred type and the line where they were defined:

```python
symbol_table = {
    "x": {"type": "int",   "line": 1},
    "y": {"type": "float", "line": 2},
}
```

Type rules:
- `/` always returns `float`, regardless of operands
- `//` returns `int` if both operands are `int`, else `float`
- `**` returns `float` if either operand is `float`, else `int`
- `+` on two strings returns `str`
- Comparisons always return `bool`
- `and`, `or`, `not` always return `bool`

The division-by-zero detection is *static only* — it only fires when the right operand is the literal `0`. If you write `x = 10 / y` and `y` happens to be `0`, SmartLint won't catch it. Catching that would require data-flow analysis, which is beyond the scope of this project. The current behavior is honest about its limits: it detects what it can detect, and doesn't pretend to do more.

### 4.4 TAC Generator

The Three-Address Code generator does a post-order traversal of the AST. Each non-trivial sub-expression gets its own temporary variable (`t1`, `t2`, ...), and each instruction has at most one operator on the right-hand side.

Example — `x = (2 + 3) * 4`:
```
t1 = 2 + 3
t2 = t1 * 4
x = t2
```

One small but meaningful design choice: **unary plus is a no-op**. If you write `x = +5`, the TAC generated is just `x = 5`. No temporary, no instruction. This is consistent with how Python actually treats unary plus.

Compound assignments expand to two instructions. `x += 5` becomes:
```
t1 = x + 5
x = t1
```

### 4.5 Optimizer

The optimizer runs multiple passes over the TAC until the output stops changing (or hits a limit of 20 iterations). Here's a quick summary of what each pass does:

**Constant folding** — evaluate operations on known literals:
```
t1 = 2 + 3     →    t1 = 5
```

**Constant propagation** — replace a variable reference with its known value:
```
x = 5
y = x          →    y = 5
```

**Algebraic simplification** — simplify using mathematical identities:
```
t1 = x + 0     →    t1 = x
t2 = x * 1     →    t2 = x
t3 = x * 0     →    t3 = 0
t4 = x ** 0    →    t4 = 1
```

**Comparison folding** — fold constant comparisons:
```
t1 = 5 > 3     →    t1 = True
t2 = 7 >= 8    →    t2 = False
```

**Boolean folding** — fold constant logical expressions:
```
t1 = True and False    →    t1 = False
t2 = not True          →    t2 = False
```

**String concatenation** — fold constant string additions:
```
t1 = 'hello' + ' world'    →    t1 = 'hello world'
```

There are safety rules the optimizer never breaks:
- Never fold `/ 0`, `// 0`, or `% 0` — leave them as-is (the semantic phase already reported the error)
- Never fold `2 ** 9999` or similar huge exponents — would cause the optimizer itself to hang
- Never propagate a constant value past the point where the variable was reassigned

---

## 5. Testing

Testing was done using pytest. The goal was to have at least one test for every language rule, and a separate test for every error condition that should be detected.

**Test breakdown:**

| Test File | # Tests | What It Covers |
|-----------|---------|----------------|
| `test_lexer.py` | 36 | Token recognition, column tracking, error handling |
| `test_parser.py` | 47 | Operator precedence, AST structure, syntax errors |
| `test_semantic.py` | 43 | Type inference, error detection, symbol table |
| `test_tac.py` | 31 | Instruction generation, order preservation |
| `test_optimizer.py` | 47 | All optimization passes, safety rules |
| `test_endtoend.py` | 38 | Full pipeline, spec regression cases |
| **Total** | **230** | |

All 230 tests pass.

The end-to-end tests include every specific case mentioned in the project specification:

| Expression | Expected | Verified |
|-----------|----------|----------|
| `2 + 3 * 4` | 14 | ✓ |
| `(2 + 3) * 4` | 20 | ✓ |
| `2 ** 3 ** 2` | 512 | ✓ |
| `-2 ** 2` | -4 | ✓ |
| `(-2) ** 2` | 4 | ✓ |
| `10 // 3` | 3 | ✓ |
| `10 % 3` | 1 | ✓ |
| `10 / 0` | ERROR: Division by zero | ✓ |
| `10 % 0` | ERROR: Modulo by zero | ✓ |
| `"hello" + " world"` | type = str | ✓ |
| `missing_var + 1` | ERROR: Undefined variable | ✓ |
| `"hello" - 2` | ERROR: Type mismatch | ✓ |
| `5 >= 3` | True | ✓ |
| `(5 > 3) and (2 < 4)` | True, type = bool | ✓ |
| `x = 5 +` | ERROR: Syntax error | ✓ |

---

## 6. The Streamlit Interface

The web interface is built with Streamlit. It's a single-page app with:

- A code editor (textarea) at the top
- A "Run Analysis" button
- A sidebar with 8 built-in example programs and a language reference panel
- A results dashboard with six tabs

The tabs let you inspect each stage individually. The Syntax Tree tab shows a human-readable indented tree rather than raw Python dict output — for example:

```
(assign 'z')  [line 3]
  (binary '+')  [line 3]
    (binary '**')  [line 3]
      (name: 'x')
      (number: 2)
    (binary '*')  [line 3]
      (name: 'y')
      (number: 4)
```

The Optimized TAC tab shows both the original instruction count and the post-optimization count, with a delta metric to quantify the improvement.

The app handles bad input gracefully — empty source, invalid characters, unclosed parentheses, type errors — without crashing or throwing a Python traceback at the user.

---

## 7. Challenges

A few things gave me more trouble than expected:

**Unary minus and exponentiation precedence.** The relationship between `-2 ** 2` and `(-2) ** 2` isn't obvious at first. Python defines `-2 ** 2 == -4` because unary minus applies *after* exponentiation. Getting this right meant placing `UMINUS` *below* `POW` in PLY's precedence table, which felt counterintuitive — you'd expect unary operators to bind tight. Once I understood that PLY's precedence table controls conflict resolution rather than direct binding strength in that context, it clicked.

**Multi-character operator tokenization.** PLY processes function-based rules before string rules, but within function rules the order they appear in the source file matters for conflict resolution. `**=` needs to beat `**` which needs to beat `*`. Getting all seven compound assignment operators and the multi-character arithmetic operators ordered correctly without any mis-tokenization took careful testing.

**Optimizer safety for division.** The first version of the optimizer folded `10 / 0` into an error state. That's wrong — the TAC for a division-by-zero expression still needs to exist in the output unchanged (because the semantic analyzer already reported it as an error, and the TAC is just a record of what was written, not an execution). The optimizer now specifically skips folding any operation with a zero divisor.

**PLY's parser table caching.** PLY writes a `parsetab.py` file to disk to speed up subsequent parser builds. This caused problems during development when I changed the grammar — the cached table was stale but PLY would use it anyway. The fix was `write_tables=False` in `yacc.yacc()`, which forces the parser to rebuild every time.

---

## 8. What Could Be Extended

If I were to continue this project, the next things I'd add are:

- **Control flow (`if`/`else`, `while`)** — This is the biggest missing piece. It would require the TAC to use labels and jump instructions, and the optimizer would need to handle basic blocks rather than just straight-line code.
- **Data-flow analysis** — Would allow catching division-by-zero through variable values, not just literals. Also enables proper dead-code elimination.
- **Symbol scoping** — Currently there's only one global scope. Adding function support would require a scope stack.
- **Better error recovery in the parser** — Right now, a syntax error in one statement often prevents subsequent statements from parsing. Standard recovery techniques (like synchronizing on newlines) would improve the diagnostic experience for multi-error programs.

---

## 9. How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the test suite
python -m pytest tests/ -v

# Launch the web interface
streamlit run app.py
```

---

## 10. Conclusion

SmartLint ended up being a more complete project than I initially planned. Implementing all five compiler stages — lexing, parsing, semantic analysis, TAC generation, and optimization — forced me to actually understand how each piece connects to the next. Reading about grammars in a textbook is one thing; debugging why `-2**2` was computing as `4` instead of `-4` because the precedence table was wrong is a different kind of learning entirely.

The 230 passing tests give a reasonable degree of confidence that the language rules are implemented consistently across all stages. Every error case that should be detected is detected. Every valid expression produces the correct intermediate code and the correct optimized output.

---

*Project built using Python 3.12, PLY 3.11, Streamlit 1.x, pytest 9.x.*
