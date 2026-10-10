
import streamlit as st
import pandas as pd

from compiler.lexer import build_lexer
from compiler.parser import parse_source
from compiler.semantic import analyze_ast
from compiler.tac import generate_tac
from compiler.optimizer import optimize_tac


# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="SmartLint | Code Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CONSTANTS AND SESSION STATE
# =========================================================
DEFAULT_SOURCE = '''\
# Welcome to SmartLint — Mini Compiler & Static Analyzer
# Supports: + - * / // % ** and or not == != < <= > >=
# Compound: += -= *= /= //= %= **=

x = 10
y = 3
z = x ** 2 + y * 4
print(z)
result = (x > y) and (z != 0)
print(result)
'''

EXAMPLES = {
    "All arithmetic ops": """\
a = 10 + 5
b = 10 - 5
c = 10 * 5
d = 10 / 5
e = 10 // 3
f = 10 % 3
g = 2 ** 3
h = -5
i = +5
j = (2 + 3) * 4
""",
    "Operator precedence": """\
x = 2 + 3 * 4
y = (2 + 3) * 4
z = 2 ** 3 ** 2
w = -2 ** 2
v = (-2) ** 2
u = 10 - 3 - 2
""",
    "Comparison & logical": """\
a = 5 > 3
b = 5 == 5
c = 5 != 3
d = 4 <= 4
e = 7 >= 8
result = (5 > 3) and (10 != 0)
neg = not result
""",
    "Compound assignments": """\
x = 10
x += 5
x -= 2
x *= 3
x //= 2
x %= 7
x **= 2
print(x)
""",
    "String operations": """\
greeting = "hello" + " " + "world"
print(greeting)
""",
    "Division by zero (error)": """\
x = 10 / 0
y = 10 % 0
z = 10 // 0
""",
    "Undefined variable (error)": """\
x = missing_var + 10
""",
    "Type error (error)": """\
x = "hello" - 2
y = True + 1
""",
    "Syntax error (error)": """\
x = 5 +
y = * 3
""",
}


def reset_source():
    """Reset the editor; callback fires before widget instantiation."""
    st.session_state["smartlint_source"] = DEFAULT_SOURCE
    st.session_state.pop("smartlint_result", None)


def load_example(name):
    """Load an example program into the editor."""
    st.session_state["smartlint_source"] = EXAMPLES[name]
    st.session_state.pop("smartlint_result", None)


if "smartlint_source" not in st.session_state:
    st.session_state["smartlint_source"] = DEFAULT_SOURCE


# =========================================================
# MODERN UI STYLING
# =========================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        font-size: 16px;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    h1 { font-size: 2.6rem !important; font-weight: 800 !important; letter-spacing: -1px; }
    h2 { font-size: 1.6rem !important; font-weight: 700 !important; }
    h3 { font-size: 1.2rem !important; font-weight: 700 !important; }
    p, label, li { font-size: 1rem; line-height: 1.65; }

    .hero {
        padding: 1.8rem 2rem;
        border-radius: 20px;
        background: linear-gradient(130deg, #0f172a 0%, #1e3a6e 55%, #1d4ed8 100%);
        color: #ffffff;
        margin-bottom: 1.5rem;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.25);
    }
    .hero h1 { color: #ffffff !important; margin: 0 0 0.4rem 0; }
    .hero .subtitle { color: #93c5fd; font-size: 1.1rem; margin: 0.2rem 0; }
    .hero .pipeline {
        color: #bfdbfe;
        font-size: 0.95rem;
        margin-top: 0.8rem;
        letter-spacing: 0.02em;
    }

    .section-card {
        border: 1px solid rgba(100, 116, 139, 0.25);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        background: rgba(248, 250, 252, 0.03);
    }

    div[data-testid="stMetric"] {
        padding: 1rem 1.2rem;
        border: 1px solid rgba(100, 116, 139, 0.25);
        border-radius: 14px;
        background: rgba(248, 250, 252, 0.03);
    }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 750; }

    div.stButton > button,
    div.stDownloadButton > button {
        min-height: 2.8rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 10px;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover { transform: translateY(-1px); }

    div[data-testid="stTextArea"] textarea {
        font-size: 15px !important;
        line-height: 1.7 !important;
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    }

    div[data-testid="stDataFrame"] { font-size: 0.95rem; }

    [data-testid="stTabs"] button {
        font-size: 0.95rem;
        font-weight: 600;
        padding-top: 0.7rem;
        padding-bottom: 0.7rem;
    }

    .diag-error {
        background: rgba(239, 68, 68, 0.08);
        border-left: 3px solid #ef4444;
        padding: 0.5rem 0.8rem;
        border-radius: 6px;
        margin: 0.3rem 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
    }
    .diag-warning {
        background: rgba(245, 158, 11, 0.08);
        border-left: 3px solid #f59e0b;
        padding: 0.5rem 0.8rem;
        border-radius: 6px;
        margin: 0.3rem 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
    }
    .diag-info {
        background: rgba(59, 130, 246, 0.06);
        border-left: 3px solid #3b82f6;
        padding: 0.5rem 0.8rem;
        border-radius: 6px;
        margin: 0.3rem 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
    }

    .footer {
        text-align: center;
        color: #64748b;
        padding-top: 2rem;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
    <div class="hero">
        <h1>🔍 SmartLint</h1>
        <p class="subtitle"><b>Mini Compiler &amp; Static Code Analyzer</b></p>
        <p class="subtitle">Detect issues. Understand your code. Optimize instructions.</p>
        <p class="pipeline">
            LEXER &nbsp;→&nbsp; PARSER &nbsp;→&nbsp; SEMANTICS &nbsp;→&nbsp; TAC &nbsp;→&nbsp; OPTIMIZER
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.caption("Customize the analysis results.")

    show_tokens = st.checkbox("Show lexical tokens", value=True)
    show_ast = st.checkbox("Show syntax tree (raw)", value=False)
    warn_type_changes = st.checkbox(
        "Warn about variable type changes",
        value=True,
    )

    st.divider()
    st.markdown("### 📋 Example Programs")
    for name in EXAMPLES:
        if st.button(name, key=f"ex_{name}", use_container_width=True):
            load_example(name)
            st.rerun()

    st.divider()
    st.markdown("### 🧠 Pipeline Stages")
    st.markdown(
        """
        1. 🔤 Lexical analysis
        2. 🌳 Syntax analysis (AST)
        3. 📚 Semantic analysis
        4. ⚙️ Three-address code
        5. 🚀 Code optimization
        """
    )
    st.divider()
    st.markdown("### 📐 Language Reference")
    st.markdown(
        """
        **Arithmetic**: `+ - * / // % **`
        **Unary**: `-x` `+x`
        **Comparison**: `== != < <= > >=`
        **Logical**: `and or not`
        **Compound**: `+= -= *= /= //= %= **=`
        **Types**: int, float, str, bool
        """
    )
    st.caption(
        "SmartLint analyzes supported source code without executing "
        "the submitted program."
    )


# =========================================================
# SOURCE EDITOR
# =========================================================
st.markdown("## 📝 Source Code Editor")
st.caption(
    "Enter code supported by the SmartLint grammar, then click **▶ Run Analysis**."
)

source = st.text_area(
    "Source code",
    key="smartlint_source",
    height=280,
    label_visibility="collapsed",
    placeholder="Write your code here…",
)

run_col, reset_col, spacer_col = st.columns([1.5, 1, 4])

with run_col:
    run_analysis = st.button(
        "▶  Run Analysis",
        type="primary",
        use_container_width=True,
    )

with reset_col:
    st.button(
        "↺  Reset",
        on_click=reset_source,
        use_container_width=True,
    )


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_diagnostic(item: dict | str) -> str:
    """Format a structured diagnostic dict or raw string for display."""
    if isinstance(item, dict):
        severity = item.get("severity", item.get("level", "INFO"))
        category = item.get("category", "")
        message  = item.get("message", str(item))
        line     = item.get("line")
        column   = item.get("column")

        parts = [str(severity).upper()]
        if category:
            parts.append(f"[{category}]")
        if line is not None:
            loc = f"Line {line}"
            if column is not None:
                loc += f":{column}"
            parts.append(f"@ {loc}")
        return f"{'  '.join(parts)}: {message}"

    return str(item)


def tokenize_source(text: str):
    """Collect tokens and lexical errors without running the source program."""
    lexer = build_lexer()
    lexer.lineno = 1
    lexer.input(text)

    token_rows = []
    while True:
        tok = lexer.token()
        if tok is None:
            break
        token_rows.append({
            "Line": tok.lineno,
            "Column": getattr(tok, "column", "—"),
            "Token Type": tok.type,
            "Value": repr(tok.value),
        })

    return token_rows, lexer.lexical_errors


def unpack_semantic_result(result):
    if isinstance(result, tuple) and len(result) >= 2:
        return result[0], result[1]
    if isinstance(result, dict):
        return result.get("symbol_table", {}), result.get("diagnostics", [])
    return getattr(result, "symbol_table", {}), getattr(result, "diagnostics", [])


def symbol_rows(table: dict) -> list:
    if isinstance(table, dict):
        rows = []
        for variable, details in table.items():
            if isinstance(details, dict):
                rows.append({"Variable": variable, **details})
            else:
                rows.append({"Variable": variable, "Details": str(details)})
        return rows
    if isinstance(table, list):
        return table
    return []


def display_diagnostics(title: str, items: list) -> None:
    st.markdown(f"### {title}")
    if not items:
        st.success("✅ No diagnostics reported.")
        return

    for item in items:
        msg = format_diagnostic(item)
        upper = msg.upper()
        if "ERROR" in upper:
            st.error(msg)
        elif "WARNING" in upper:
            st.warning(msg)
        else:
            st.info(msg)


def is_error(item) -> bool:
    return "ERROR" in format_diagnostic(item).upper()


def is_warning(item) -> bool:
    return "WARNING" in format_diagnostic(item).upper()


def ast_to_text(node, indent: int = 0) -> str:
    """Pretty-print an AST node as indented text."""
    pad = "  " * indent
    if not isinstance(node, dict):
        return f"{pad}{node!r}"

    ntype = node.get("type", "?")
    line  = node.get("line", "")
    line_info = f"  [line {line}]" if line else ""

    if ntype in ("number", "string", "boolean", "name"):
        return f"{pad}({ntype}: {node.get('value')!r}){line_info}"

    if ntype == "unary":
        op = node.get("operator")
        child = ast_to_text(node.get("value", {}), indent + 1)
        return f"{pad}(unary {op!r}){line_info}\n{child}"

    if ntype in ("binary", "compare"):
        op    = node.get("operator")
        left  = ast_to_text(node.get("left",  {}), indent + 1)
        right = ast_to_text(node.get("right", {}), indent + 1)
        return f"{pad}({ntype} {op!r}){line_info}\n{left}\n{right}"

    if ntype in ("logical_and", "logical_or"):
        left  = ast_to_text(node.get("left",  {}), indent + 1)
        right = ast_to_text(node.get("right", {}), indent + 1)
        return f"{pad}({ntype}){line_info}\n{left}\n{right}"

    if ntype == "logical_not":
        child = ast_to_text(node.get("value", {}), indent + 1)
        return f"{pad}(logical_not){line_info}\n{child}"

    if ntype == "assign":
        name  = node.get("name")
        child = ast_to_text(node.get("value", {}), indent + 1)
        return f"{pad}(assign {name!r}){line_info}\n{child}"

    if ntype == "compound":
        name  = node.get("name")
        op    = node.get("operator")
        child = ast_to_text(node.get("value", {}), indent + 1)
        return f"{pad}(compound {name!r} {op!r}=){line_info}\n{child}"

    if ntype == "print":
        child = ast_to_text(node.get("value", {}), indent + 1)
        return f"{pad}(print){line_info}\n{child}"

    return f"{pad}{node!r}{line_info}"


# =========================================================
# RUN ANALYSIS
# =========================================================
if run_analysis:
    if not source.strip():
        st.warning("Please enter some source code before running analysis.")
    else:
        st.session_state.pop("smartlint_result", None)

        try:
            # Stage 1: Lexer
            token_rows, lexical_errors = tokenize_source(source)

            # Stage 2: Parser
            ast_tree, parse_errors = parse_source(source)
            parse_errors = list(parse_errors or [])

            # Separate lexical errors that came back through parse_source
            all_lex = lexical_errors
            syntax_errs = [e for e in parse_errors if e.get("category") == "SYNTAX"]

            if ast_tree is None:
                ast_tree = []

            result = {
                "tokens": token_rows,
                "lexical_errors": all_lex,
                "ast": ast_tree,
                "syntax_errors": syntax_errs,
                "symbol_table": {},
                "semantic_diagnostics": [],
                "tac": [],
                "optimized_tac": [],
                "semantic_error": None,
                "tac_error": None,
            }

            blocking_errors = all_lex + syntax_errs

            if not blocking_errors:
                # Stage 3: Semantic analysis
                try:
                    semantic_result = analyze_ast(
                        ast_tree,
                        warn_type_changes=warn_type_changes,
                    )
                    symbols, semantic_diagnostics = unpack_semantic_result(
                        semantic_result
                    )
                    result["symbol_table"] = symbols or {}
                    result["semantic_diagnostics"] = list(semantic_diagnostics or [])
                except Exception as exc:
                    result["semantic_error"] = str(exc)

                # Stage 4 & 5: TAC + Optimization
                try:
                    tac = generate_tac(ast_tree)
                    result["tac"] = list(tac or [])
                    optimized = optimize_tac(result["tac"])
                    result["optimized_tac"] = list(optimized or [])
                except Exception as exc:
                    result["tac_error"] = str(exc)

            st.session_state["smartlint_result"] = result

        except Exception as exc:
            st.error("The analysis pipeline encountered an unexpected error.")
            st.code(f"{type(exc).__name__}: {exc}", language="text")


# =========================================================
# RESULTS DASHBOARD
# =========================================================
result = st.session_state.get("smartlint_result")

if result:
    st.divider()
    st.markdown("## 📊 Analysis Dashboard")

    lexical_errors        = result["lexical_errors"]
    syntax_errors         = result["syntax_errors"]
    semantic_diagnostics  = result["semantic_diagnostics"]

    all_diagnostics = lexical_errors + syntax_errors + semantic_diagnostics

    error_count   = sum(is_error(d)   for d in all_diagnostics)
    warning_count = sum(is_warning(d) for d in all_diagnostics)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🔤 Tokens",          len(result["tokens"]))
    m2.metric("🌳 AST Nodes",        len(result["ast"]))
    m3.metric("❌ Errors",           error_count)
    m4.metric("⚠️ Warnings",         warning_count)
    m5.metric("⚙️ TAC Instructions", len(result["tac"]))

    if lexical_errors or syntax_errors:
        st.error(
            "🚫 Lexical or syntax errors detected. "
            "Fix these before generating intermediate code."
        )
    elif result["semantic_error"] or result["tac_error"]:
        st.warning(
            "⚠️ Some analysis stages did not complete. "
            "Review the stage-specific details below."
        )
    elif error_count:
        st.warning(
            "⚠️ Analysis completed with semantic errors. "
            "Review the diagnostics before relying on the output."
        )
    else:
        st.success("✅ Analysis pipeline completed successfully.")

    tabs = st.tabs(
        [
            "🩺 Diagnostics",
            "🔤 Tokens",
            "🌳 Syntax Tree",
            "📚 Symbol Table",
            "⚙️ TAC",
            "🚀 Optimized TAC",
        ]
    )

    # ----------------------------------------------------------
    # DIAGNOSTICS
    # ----------------------------------------------------------
    with tabs[0]:
        display_diagnostics("Lexical Diagnostics", lexical_errors)
        display_diagnostics("Syntax Diagnostics", syntax_errors)

        st.markdown("### Semantic Diagnostics")
        if result["semantic_error"]:
            st.error(
                "Semantic analysis could not complete: " + result["semantic_error"]
            )
        elif semantic_diagnostics:
            for item in semantic_diagnostics:
                message = format_diagnostic(item)
                if is_error(item):
                    st.error(message)
                elif is_warning(item):
                    st.warning(message)
                else:
                    st.info(message)
        elif lexical_errors or syntax_errors:
            st.info("ℹ️ Semantic analysis was skipped due to earlier errors.")
        else:
            st.success("✅ No semantic diagnostics reported.")

        if result["tac_error"]:
            st.error("TAC/optimization stage failed: " + result["tac_error"])

    # ----------------------------------------------------------
    # TOKENS
    # ----------------------------------------------------------
    with tabs[1]:
        st.markdown("### Lexical Tokens")
        if not show_tokens:
            st.info("Enable 'Show lexical tokens' in the sidebar.")
        elif result["tokens"]:
            st.dataframe(
                pd.DataFrame(result["tokens"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No tokens were produced.")

    # ----------------------------------------------------------
    # SYNTAX TREE
    # ----------------------------------------------------------
    with tabs[2]:
        st.markdown("### Abstract Syntax Tree")
        if syntax_errors or lexical_errors:
            st.info("Fix lexical and syntax errors to inspect the syntax tree.")
        elif not result["ast"]:
            st.info("No AST was produced.")
        else:
            if show_ast:
                st.code(repr(result["ast"]), language="python")
            else:
                lines = [ast_to_text(node) for node in result["ast"]]
                st.code("\n\n".join(lines), language="text")

    # ----------------------------------------------------------
    # SYMBOL TABLE
    # ----------------------------------------------------------
    with tabs[3]:
        st.markdown("### Symbol Table")
        rows = symbol_rows(result["symbol_table"])
        if rows:
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )
        elif lexical_errors or syntax_errors:
            st.info("Symbol table unavailable until parsing succeeds.")
        elif result["semantic_error"]:
            st.error(result["semantic_error"])
        else:
            st.info("No variables were recorded.")

    # ----------------------------------------------------------
    # ORIGINAL TAC
    # ----------------------------------------------------------
    with tabs[4]:
        st.markdown("### Three-Address Code")
        if result["tac"]:
            tac_text = "\n".join(map(str, result["tac"]))
            st.code(tac_text, language="text")
            st.download_button(
                "⬇ Download TAC",
                data=tac_text,
                file_name="smartlint_tac.txt",
                mime="text/plain",
                use_container_width=True,
            )
        elif result["tac_error"]:
            st.error(result["tac_error"])
        elif lexical_errors or syntax_errors:
            st.info("TAC was not generated due to earlier errors.")
        else:
            st.info("No TAC instructions were produced.")

    # ----------------------------------------------------------
    # OPTIMIZED TAC
    # ----------------------------------------------------------
    with tabs[5]:
        st.markdown("### Optimized Three-Address Code")
        if result["optimized_tac"]:
            optimized_text = "\n".join(map(str, result["optimized_tac"]))
            st.code(optimized_text, language="text")
            st.download_button(
                "⬇ Download Optimized TAC",
                data=optimized_text,
                file_name="smartlint_optimized_tac.txt",
                mime="text/plain",
                use_container_width=True,
            )

            original_count  = len(result["tac"])
            optimized_count = len(result["optimized_tac"])

            st.markdown("#### Instruction Comparison")
            c1, c2 = st.columns(2)
            c1.metric("Before Optimization", original_count)
            c2.metric(
                "After Optimization",
                optimized_count,
                delta=optimized_count - original_count,
                delta_color="inverse",
            )

            if original_count:
                change = original_count - optimized_count
                if change > 0:
                    st.success(f"🚀 {change} fewer instruction(s) after optimization.")
                elif change == 0:
                    st.info("The instruction count did not change.")
                else:
                    st.info("The optimized output contains more instructions; review the generated code.")

        elif result["tac_error"]:
            st.error(result["tac_error"])
        elif lexical_errors or syntax_errors:
            st.info("Optimized TAC not available due to earlier errors.")
        else:
            st.info("Optimized TAC is not available.")

else:
    st.markdown(
        """
        <div class="section-card">
            <h3>🚀 Ready to analyze?</h3>
            <p>
                Enter a program in the editor and click
                <b>▶ Run Analysis</b> to inspect tokens, the syntax tree,
                semantic diagnostics, symbol table, three-address code,
                and optimization results.
            </p>
            <p>
                Or select one of the <b>Example Programs</b> from the sidebar
                to see the supported language features in action.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="footer">
        SmartLint · Mini Compiler and Static Code Analyzer<br>
        Built with Python, PLY and Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
