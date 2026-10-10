"""
SmartLint Semantic Analyzer
============================
Performs semantic validation on the AST produced by the parser.

Checks performed
----------------
- Undefined variable detection (variable must be assigned before use)
- Type inference and type compatibility for all operators
- Division by zero (static, when right operand is literal 0)
- Floor-division by zero (static)
- Modulo by zero (static)
- Invalid arithmetic: bool NOT treated as numeric
- Invalid arithmetic: str only supports + (concatenation)
- Compound assignment on undefined variable
- Comparison type compatibility
- Logical expression type checking
- Unary operator compatibility
- Optional: warning when a variable changes its type

Type system (dynamic, inferred)
--------------------------------
  int   — integer literal or integer expression
  float — float literal or expression involving float
  str   — string literal or string concatenation
  bool  — boolean literal, comparison result, logical result
  None  — unknown (error already reported; suppress cascading errors)

Design notes
------------
- bool is NOT numeric: arithmetic on bool operands raises an error
- str only supports + (concatenation of two strs)
- Division always returns float
- // returns int when both operands are int, else float
- % returns same type as left operand (if both numeric)
- ** returns float if either operand is float, else int
- Comparisons always return bool
- Logical ops return bool (for the purposes of this type system)
"""

from __future__ import annotations

from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NUMERIC_TYPES = ("int", "float")


def _is_numeric(t: Optional[str]) -> bool:
    return t in NUMERIC_TYPES


def _is_zero_literal(node: dict) -> bool:
    """Return True when *node* is a literal 0 or 0.0."""
    if node["type"] == "number":
        return node["value"] == 0
    return False


def _make_diag(severity: str, category: str, message: str, line, column=None) -> dict:
    return {
        "severity": severity,
        "category": category,
        "message": message,
        "line": line,
        "column": column,
    }


# ---------------------------------------------------------------------------
# Analyzer class
# ---------------------------------------------------------------------------

class SemanticAnalyzer:
    def __init__(self, warn_type_changes: bool = True):
        self.symbol_table: dict[str, dict] = {}
        self.diagnostics: list[dict] = []
        self.warn_type_changes = warn_type_changes

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------

    def _error(self, line, message: str, column=None) -> None:
        self.diagnostics.append(
            _make_diag("ERROR", "SEMANTIC", message, line, column)
        )

    def _warning(self, line, message: str, column=None) -> None:
        self.diagnostics.append(
            _make_diag("WARNING", "SEMANTIC", message, line, column)
        )

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyze(self, ast) -> tuple[dict, list]:
        self.symbol_table = {}
        self.diagnostics = []

        if ast is not None:
            for statement in ast:
                self.check_statement(statement)

        return self.symbol_table, self.diagnostics

    # ------------------------------------------------------------------
    # Statement handlers
    # ------------------------------------------------------------------

    def check_statement(self, statement: dict) -> None:
        stype = statement["type"]
        line = statement.get("line", 1)

        if stype == "assign":
            self._handle_assign(statement, line)

        elif stype == "compound":
            self._handle_compound(statement, line)

        elif stype == "print":
            self.infer_type(statement["value"])

    def _handle_assign(self, stmt: dict, line) -> None:
        name = stmt["name"]
        value_type = self.infer_type(stmt["value"])

        if value_type is None:
            # Error already reported by infer_type; don't store a broken type
            return

        previous = self.symbol_table.get(name)
        if (
            previous is not None
            and previous["type"] != value_type
            and self.warn_type_changes
        ):
            self._warning(
                line,
                f"Variable '{name}' changes type from "
                f"{previous['type']} to {value_type}",
            )

        self.symbol_table[name] = {"type": value_type, "line": line}

    def _handle_compound(self, stmt: dict, line) -> None:
        """
        Validate  name OP= expr.
        Requires 'name' to be defined; then checks that 'name OP expr'
        would be type-valid and updates the symbol table.
        """
        name = stmt["name"]
        operator = stmt["operator"]

        if name not in self.symbol_table:
            self._error(
                line,
                f"Variable '{name}' is used before it is defined",
            )
            return

        # Synthesize a binary expression to re-use infer_type logic
        synthetic = {
            "type": "binary",
            "operator": operator,
            "left": {
                "type": "name",
                "value": name,
                "line": line,
            },
            "right": stmt["value"],
            "line": line,
        }
        result_type = self.infer_type(synthetic)

        if result_type is not None:
            self.symbol_table[name] = {"type": result_type, "line": line}

    # ------------------------------------------------------------------
    # Type inference
    # ------------------------------------------------------------------

    def infer_type(self, expr: dict) -> Optional[str]:
        """Return the inferred type string, or None if an error was reported."""
        etype = expr["type"]
        line = expr.get("line", 1)

        if etype == "number":
            return "float" if isinstance(expr["value"], float) else "int"

        if etype == "string":
            return "str"

        if etype == "boolean":
            return "bool"

        if etype == "name":
            return self._infer_name(expr, line)

        if etype == "unary":
            return self._infer_unary(expr, line)

        if etype == "binary":
            return self._infer_binary(expr, line)

        if etype == "compare":
            return self._infer_compare(expr, line)

        if etype == "logical_and":
            return self._infer_logical_binary(expr, "and", line)

        if etype == "logical_or":
            return self._infer_logical_binary(expr, "or", line)

        if etype == "logical_not":
            return self._infer_logical_not(expr, line)

        self._error(line, f"Unknown expression type: {etype!r}")
        return None

    # ------------------------------------------------------------------
    # Sub-type inferrers
    # ------------------------------------------------------------------

    def _infer_name(self, expr: dict, line) -> Optional[str]:
        name = expr["value"]
        if name not in self.symbol_table:
            self._error(line, f"Variable '{name}' is used before it is defined")
            return None
        return self.symbol_table[name]["type"]

    def _infer_unary(self, expr: dict, line) -> Optional[str]:
        operator = expr["operator"]
        operand_type = self.infer_type(expr["value"])

        if operand_type is None:
            return None  # cascading error suppressed

        if operand_type == "bool":
            self._error(
                line,
                f"Unary '{operator}' cannot be applied to bool",
            )
            return None

        if operand_type not in NUMERIC_TYPES:
            self._error(
                line,
                f"Unary '{operator}' cannot be applied to {operand_type}",
            )
            return None

        return operand_type  # unary +/- preserves numeric type

    def _infer_binary(self, expr: dict, line) -> Optional[str]:
        operator = expr["operator"]
        left_type = self.infer_type(expr["left"])
        right_type = self.infer_type(expr["right"])

        if left_type is None or right_type is None:
            return None  # cascading error suppressed

        # ---- string concatenation ----------------------------------------
        if operator == "+" and left_type == right_type == "str":
            return "str"

        # ---- reject bool in arithmetic ------------------------------------
        if left_type == "bool" or right_type == "bool":
            self._error(
                line,
                f"Operator '{operator}' cannot be applied to bool operands",
            )
            return None

        # ---- reject non-numeric types in arithmetic -----------------------
        if not _is_numeric(left_type) or not _is_numeric(right_type):
            self._error(
                line,
                f"Operator '{operator}' cannot be applied to "
                f"{left_type} and {right_type}",
            )
            return None

        # ---- division-by-zero checks (static only) -----------------------
        if operator in ("/", "//", "%") and _is_zero_literal(expr["right"]):
            verb = {
                "/": "Division",
                "//": "Floor division",
                "%": "Modulo",
            }[operator]
            self._error(line, f"{verb} by zero")
            return None

        # ---- result type --------------------------------------------------
        if operator == "/":
            return "float"

        if operator in ("//", "%"):
            if "float" in (left_type, right_type):
                return "float"
            return "int"

        if operator == "**":
            if "float" in (left_type, right_type):
                return "float"
            return "int"

        # + - *
        if "float" in (left_type, right_type):
            return "float"
        return "int"

    def _infer_compare(self, expr: dict, line) -> Optional[str]:
        operator = expr["operator"]
        left_type = self.infer_type(expr["left"])
        right_type = self.infer_type(expr["right"])

        if left_type is None or right_type is None:
            return None

        # Allow same types always; allow numeric cross-types
        if left_type == right_type:
            return "bool"

        if _is_numeric(left_type) and _is_numeric(right_type):
            return "bool"

        # Reject incompatible comparisons
        self._error(
            line,
            f"Operator '{operator}' cannot compare {left_type} and {right_type}",
        )
        return None

    def _infer_logical_binary(self, expr: dict, operator: str, line) -> Optional[str]:
        # and/or: both operands can be any type; result is bool
        left_type = self.infer_type(expr["left"])
        right_type = self.infer_type(expr["right"])

        if left_type is None or right_type is None:
            return None

        return "bool"

    def _infer_logical_not(self, expr: dict, line) -> Optional[str]:
        operand_type = self.infer_type(expr["value"])
        if operand_type is None:
            return None
        return "bool"


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def analyze_ast(ast, warn_type_changes: bool = True) -> tuple[dict, list]:
    """Analyze *ast* and return ``(symbol_table, diagnostics)``."""
    analyzer = SemanticAnalyzer(warn_type_changes=warn_type_changes)
    return analyzer.analyze(ast)
