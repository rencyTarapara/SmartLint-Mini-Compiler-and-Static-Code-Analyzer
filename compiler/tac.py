"""
SmartLint TAC Generator
========================
Translates the AST into Three-Address Code (TAC).

TAC format
----------
  target = operand                      # copy / literal
  target = op operand                   # unary
  target = left op right                # binary / compare / logical
  print operand                         # output

Temporaries are named t1, t2, … in order of creation.

Node → TAC mapping
------------------
  assign      name = <expr>
  compound    t1 = name OP val ; name = t1
  print       print <expr>
  binary      t1 = left OP right
  compare     t1 = left OP right
  logical_and t1 = left and right
  logical_or  t1 = left or right
  logical_not t1 = not operand
  unary '-'   t1 = -<operand>          (literal folded inline if possible)
  unary '+'   no instruction, operand returned directly
  number      repr(value)
  string      repr(value)
  boolean     'True' / 'False'
  name        variable name

Unary minus normalisation
-------------------------
  When the operand is already a numeric literal, the unary node is lowered
  to a single literal string (e.g. "-5" or "-3.14") so the instruction
  becomes ``t1 = -5`` rather than an explicit unary instruction.
  When the operand is a non-literal, the instruction is ``t1 = -<temp>``.
"""

from __future__ import annotations


class TACGenerator:
    def __init__(self) -> None:
        self.instructions: list[str] = []
        self.temp_count: int = 0

    # ------------------------------------------------------------------
    # Temporary variable factory
    # ------------------------------------------------------------------

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"t{self.temp_count}"

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(self, ast) -> list[str]:
        self.instructions = []
        self.temp_count = 0

        if ast is None:
            return []

        for statement in ast:
            self.generate_statement(statement)

        return list(self.instructions)

    # ------------------------------------------------------------------
    # Statement generators
    # ------------------------------------------------------------------

    def generate_statement(self, statement: dict) -> None:
        stype = statement["type"]

        if stype == "assign":
            name = statement["name"]
            value = self.generate_expression(statement["value"])
            self.instructions.append(f"{name} = {value}")

        elif stype == "compound":
            # x OP= expr  →  t1 = x OP expr ; x = t1
            name = statement["name"]
            operator = statement["operator"]
            rhs = self.generate_expression(statement["value"])
            temp = self.new_temp()
            self.instructions.append(f"{temp} = {name} {operator} {rhs}")
            self.instructions.append(f"{name} = {temp}")

        elif stype == "print":
            value = self.generate_expression(statement["value"])
            self.instructions.append(f"print {value}")

    # ------------------------------------------------------------------
    # Expression generators
    # ------------------------------------------------------------------

    def generate_expression(self, expr: dict) -> str:
        """Generate TAC instructions for *expr* and return the result operand."""
        etype = expr["type"]

        if etype == "number":
            return self._format_number(expr["value"])

        if etype == "string":
            return repr(expr["value"])

        if etype == "boolean":
            return "True" if expr["value"] else "False"

        if etype == "name":
            return expr["value"]

        if etype == "unary":
            return self._generate_unary(expr)

        if etype == "binary":
            return self._generate_binary(expr)

        if etype == "compare":
            return self._generate_binary(expr)  # same structure as binary

        if etype == "logical_and":
            left = self.generate_expression(expr["left"])
            right = self.generate_expression(expr["right"])
            temp = self.new_temp()
            self.instructions.append(f"{temp} = {left} and {right}")
            return temp

        if etype == "logical_or":
            left = self.generate_expression(expr["left"])
            right = self.generate_expression(expr["right"])
            temp = self.new_temp()
            self.instructions.append(f"{temp} = {left} or {right}")
            return temp

        if etype == "logical_not":
            operand = self.generate_expression(expr["value"])
            temp = self.new_temp()
            self.instructions.append(f"{temp} = not {operand}")
            return temp

        raise ValueError(f"Unsupported expression type: {etype!r}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_number(value) -> str:
        """Format a numeric literal cleanly (no trailing .0 for int-valued floats when avoidable)."""
        if isinstance(value, int):
            return str(value)
        # float: use repr to preserve precision
        return repr(value)

    def _generate_unary(self, expr: dict) -> str:
        operator = expr["operator"]
        inner = expr["value"]

        if operator == "+":
            # Unary plus is a no-op; just return the operand
            return self.generate_expression(inner)

        # Unary minus
        if inner["type"] == "number":
            # Fold directly into a literal to get: t1 = -5  (not t1 = - 5)
            raw = self._format_number(inner["value"])
            temp = self.new_temp()
            self.instructions.append(f"{temp} = -{raw}")
            return temp

        operand = self.generate_expression(inner)
        temp = self.new_temp()
        self.instructions.append(f"{temp} = -{operand}")
        return temp

    def _generate_binary(self, expr: dict) -> str:
        left = self.generate_expression(expr["left"])
        right = self.generate_expression(expr["right"])
        operator = expr["operator"]
        temp = self.new_temp()
        self.instructions.append(f"{temp} = {left} {operator} {right}")
        return temp


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def generate_tac(ast) -> list[str]:
    """Generate TAC for *ast* and return the instruction list."""
    return TACGenerator().generate(ast)
