
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
DEFAULT_SOURCE = '''# Welcome to SmartLint
# Enter code supported by the SmartLint grammar.

x = 10
y = 20
z = x + y * 2
print(z)
'''


def reset_source():
    """Reset the editor using a callback before widgets are instantiated."""
    st.session_state["smartlint_source"] = DEFAULT_SOURCE
    st.session_state.pop("smartlint_result", None)


if "smartlint_source" not in st.session_state:
    st.session_state["smartlint_source"] = DEFAULT_SOURCE


# =========================================================
# MODERN UI STYLING
# =========================================================
st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-size: 18px;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.8rem;
        padding-bottom: 3rem;
    }

    h1 {
        font-size: 2.7rem !important;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }

    h2 {
        font-size: 1.8rem !important;
        font-weight: 750 !important;
    }

    h3 {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }

    p, label, li {
        font-size: 1.05rem;
        line-height: 1.65;
    }

    .hero {
        padding: 2rem 2.2rem;
        border-radius: 20px;
        background: linear-gradient(125deg, #101b3f 0%, #174ea6 65%, #2879d8 100%);
        color: #ffffff;
        margin-bottom: 1.5rem;
        box-shadow: 0 12px 30px rgba(20, 50, 110, 0.18);
    }

    .hero h1 {
        color: #ffffff !important;
        margin: 0 0 0.5rem 0;
    }

    .hero p {
        color: #e2eaff;
        margin: 0.3rem 0;
        font-size: 1.12rem;
    }

    .section-card {
        border: 1px solid rgba(128, 128, 128, 0.28);
        border-radius: 15px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }

    div[data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        border: 1px solid rgba(128, 128, 128, 0.28);
        border-radius: 14px;
        background: rgba(128, 128, 128, 0.04);
    }

    div[data-testid="stMetricLabel"] {
        font-size: 1rem;
    }

    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 750;
    }

    div.stButton > button,
    div.stDownloadButton > button {
        min-height: 3rem;
        font-size: 1.05rem;
        font-weight: 650;
        border-radius: 10px;
    }

    div[data-testid="stTextArea"] textarea {
        font-size: 17px !important;
        line-height: 1.65 !important;
        font-family: Consolas, "Courier New", monospace !important;
    }

    div[data-testid="stDataFrame"] {
        font-size: 1rem;
    }

    [data-testid="stTabs"] button {
        font-size: 1rem;
        font-weight: 650;
        padding-top: 0.8rem;
        padding-bottom: 0.8rem;
    }

    .footer {
        text-align: center;
        color: #8b95a7;
        padding-top: 1.5rem;
        font-size: 0.95rem;
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
        <p><b>Mini Compiler & Static Code Analyzer</b></p>
        <p>Understand your code. Detect issues. Optimize instructions.</p>
        <p>LEXER &nbsp; → &nbsp; PARSER &nbsp; → &nbsp; SEMANTICS
        &nbsp; → &nbsp; TAC &nbsp; → &nbsp; OPTIMIZER</p>
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
    show_ast = st.checkbox("Show syntax tree", value=True)
    warn_type_changes = st.checkbox(
        "Warn about variable type changes",
        value=True,
    )

    st.divider()

    st.markdown("### 🧠 Analysis Pipeline")
    st.markdown(
        """
        1. 🔤 Lexical analysis
        2. 🌳 Syntax analysis
        3. 📚 Semantic analysis
        4. ⚙️ Three-address code
        5. 🚀 Code optimization
        """
    )

    st.divider()
    st.caption(
        "SmartLint analyzes supported source code without executing "
        "the submitted program."
    )


# =========================================================
# SOURCE EDITOR
# =========================================================
st.markdown("## 📝 Source Code Editor")
st.caption(
    "Enter code supported by the SmartLint grammar, then run the analysis."
)

source = st.text_area(
    "Source code",
    key="smartlint_source",
    height=300,
    label_visibility="collapsed",
    placeholder="Write your code here...",
)

run_col, reset_col, spacer_col = st.columns([1.5, 1, 4])

with run_col:
    run_analysis = st.button(
        "▶  Run Analysis",
        type="primary",
        width="stretch",
    )

with reset_col:
    # The callback runs before the next script execution and before
    # the text-area widget is instantiated again.
    st.button(
        "↺  Reset",
        on_click=reset_source,
        width="stretch",
    )


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def format_diagnostic(item):
    """Format a string or dictionary diagnostic for display."""
    if isinstance(item, dict):
        severity = item.get(
            "severity",
            item.get("level", item.get("type", "INFO")),
        )
        message = item.get(
            "message",
            item.get("error", str(item)),
        )
        line = item.get("line")

        prefix = str(severity).upper()
        if line is not None:
            prefix += f" · Line {line}"

        return f"{prefix}: {message}"

    return str(item)


def tokenize_source(text):
    """Collect tokens without running the source program."""
    lexer = build_lexer()
    lexer.lineno = 1
    lexer.input(text)

    token_rows = []

    while True:
        token = lexer.token()
        if token is None:
            break

        token_rows.append(
            {
                "Line": token.lineno,
                "Token Type": token.type,
                "Value": repr(token.value),
            }
        )

    lexical_errors = []
    for attr in ("errors", "lexical_errors", "lexer_errors"):
        value = getattr(lexer, attr, None)
        if isinstance(value, list):
            lexical_errors = list(value)
            break

    return token_rows, lexical_errors


def unpack_semantic_result(result):
    """Accept common symbol-table/diagnostic result formats."""
    if isinstance(result, tuple) and len(result) >= 2:
        return result[0], result[1]

    if isinstance(result, dict):
        return (
            result.get("symbol_table", {}),
            result.get("diagnostics", []),
        )

    return (
        getattr(result, "symbol_table", {}),
        getattr(result, "diagnostics", []),
    )


def symbol_rows(table):
    """Convert a symbol table into rows suitable for display."""
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


def display_diagnostics(title, items):
    """Display diagnostic messages using severity-based styling."""
    st.markdown(f"### {title}")

    if not items:
        st.success("No diagnostics reported.")
        return

    for item in items:
        message = format_diagnostic(item)
        upper = message.upper()

        if "ERROR" in upper:
            st.error(message)
        elif "WARNING" in upper:
            st.warning(message)
        else:
            st.info(message)


def is_error(item):
    return "ERROR" in format_diagnostic(item).upper()


def is_warning(item):
    return "WARNING" in format_diagnostic(item).upper()


# =========================================================
# RUN ANALYSIS
# =========================================================
if run_analysis:
    if not source.strip():
        st.warning("Please enter some source code before running analysis.")
    else:
        # Avoid showing stale output if the next run fails.
        st.session_state.pop("smartlint_result", None)

        try:
            # Stage 1: Lexer
            token_rows, lexical_errors = tokenize_source(source)

            # Stage 2: Parser
            ast_tree, syntax_errors = parse_source(source)
            syntax_errors = list(syntax_errors or [])

            if ast_tree is None:
                ast_tree = []

            result = {
                "tokens": token_rows,
                "lexical_errors": lexical_errors,
                "ast": ast_tree,
                "syntax_errors": syntax_errors,
                "symbol_table": {},
                "semantic_diagnostics": [],
                "tac": [],
                "optimized_tac": [],
                "semantic_error": None,
                "tac_error": None,
            }

            # Only continue if lexical and syntax analysis succeeded.
            if not lexical_errors and not syntax_errors:
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
                    result["semantic_diagnostics"] = list(
                        semantic_diagnostics or []
                    )
                except Exception as exc:
                    result["semantic_error"] = str(exc)

                # Stage 4: TAC generation
                try:
                    tac = generate_tac(ast_tree)
                    result["tac"] = list(tac or [])

                    # Stage 5: Optimization
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

    lexical_errors = result["lexical_errors"]
    syntax_errors = result["syntax_errors"]
    semantic_diagnostics = result["semantic_diagnostics"]

    all_diagnostics = (
        lexical_errors + syntax_errors + semantic_diagnostics
    )

    error_count = sum(is_error(item) for item in all_diagnostics)
    warning_count = sum(is_warning(item) for item in all_diagnostics)

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("🔤 Tokens", len(result["tokens"]))
    m2.metric("❌ Errors", error_count)
    m3.metric("⚠️ Warnings", warning_count)
    m4.metric("⚙️ TAC Instructions", len(result["tac"]))

    if lexical_errors or syntax_errors:
        st.error(
            "Lexical or syntax errors were detected. "
            "Fix these before generating intermediate code."
        )
    elif result["semantic_error"] or result["tac_error"]:
        st.warning(
            "Some analysis stages did not complete. "
            "Review the stage-specific details below."
        )
    elif error_count:
        st.warning(
            "Analysis completed with semantic errors. "
            "Review the diagnostics before relying on the output."
        )
    else:
        st.success("Analysis pipeline completed.")

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

    # -----------------------------------------------------
    # DIAGNOSTICS
    # -----------------------------------------------------
    with tabs[0]:
        display_diagnostics("Lexical Diagnostics", lexical_errors)
        display_diagnostics("Syntax Diagnostics", syntax_errors)

        st.markdown("### Semantic Diagnostics")
        if result["semantic_error"]:
            st.error(
                "Semantic analysis could not complete: "
                + result["semantic_error"]
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
            st.info("Semantic analysis was skipped due to earlier errors.")
        else:
            st.success("No semantic diagnostics reported.")

        if result["tac_error"]:
            st.error("TAC/optimization stage failed: " + result["tac_error"])

    # -----------------------------------------------------
    # TOKENS
    # -----------------------------------------------------
    with tabs[1]:
        st.markdown("### Lexical Tokens")

        if not show_tokens:
            st.info("Enable 'Show lexical tokens' in the sidebar.")
        elif result["tokens"]:
            st.dataframe(
                pd.DataFrame(result["tokens"]),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No tokens were produced.")

    # -----------------------------------------------------
    # SYNTAX TREE
    # -----------------------------------------------------
    with tabs[2]:
        st.markdown("### Abstract Syntax Tree")

        if not show_ast:
            st.info("Enable 'Show syntax tree' in the sidebar.")
        elif syntax_errors or lexical_errors:
            st.info("Fix lexical and syntax errors to inspect the syntax tree.")
        else:
            st.code(repr(result["ast"]), language="python")

    # -----------------------------------------------------
    # SYMBOL TABLE
    # -----------------------------------------------------
    with tabs[3]:
        st.markdown("### Symbol Table")

        rows = symbol_rows(result["symbol_table"])

        if rows:
            st.dataframe(
                pd.DataFrame(rows),
                width="stretch",
                hide_index=True,
            )
        elif lexical_errors or syntax_errors:
            st.info("The symbol table is unavailable until parsing succeeds.")
        elif result["semantic_error"]:
            st.error(result["semantic_error"])
        else:
            st.info("No variables were recorded.")

    # -----------------------------------------------------
    # ORIGINAL TAC
    # -----------------------------------------------------
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
                width="stretch",
            )
        elif result["tac_error"]:
            st.error(result["tac_error"])
        else:
            st.info("TAC was not generated.")

    # -----------------------------------------------------
    # OPTIMIZED TAC
    # -----------------------------------------------------
    with tabs[5]:
        st.markdown("### Optimized Three-Address Code")

        if result["optimized_tac"]:
            optimized_text = "\n".join(
                map(str, result["optimized_tac"])
            )
            st.code(optimized_text, language="text")

            st.download_button(
                "⬇ Download Optimized TAC",
                data=optimized_text,
                file_name="smartlint_optimized_tac.txt",
                mime="text/plain",
                width="stretch",
            )

            original_count = len(result["tac"])
            optimized_count = len(result["optimized_tac"])

            st.markdown("#### Instruction Comparison")
            c1, c2 = st.columns(2)
            c1.metric("Before Optimization", original_count)
            c2.metric("After Optimization", optimized_count)

            if original_count:
                change = original_count - optimized_count
                if change > 0:
                    st.success(
                        f"{change} fewer instruction(s) in the optimized output."
                    )
                elif change == 0:
                    st.info("The instruction count did not change.")
                else:
                    st.info(
                        "The optimized output contains more instructions; "
                        "review the generated code."
                    )
        elif result["tac_error"]:
            st.error(result["tac_error"])
        else:
            st.info("Optimized TAC is not available.")

else:
    st.markdown(
        """
        <div class="section-card">
            <h3>🚀 Ready to analyze?</h3>
            <p>
                Enter a program in the editor and click
                <b>Run Analysis</b> to inspect tokens, diagnostics,
                variables, intermediate code and optimization results.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="footer">
        SmartLint · Mini Compiler and Static Code Analyzer
        <br>
        Built with Python, PLY and Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
