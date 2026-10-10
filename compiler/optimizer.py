"""
SmartLint TAC Optimizer
========================
Optimizes TAC instructions without changing observable program behaviour.

Optimization passes (applied in a single combined forward scan,
iterated until stable)
----------------------------------------------------------------------
1. Constant folding        — evaluate binary ops on known constants
2. Constant propagation    — replace a variable with its known constant value
3. Copy propagation        — replace a variable copy with the source variable
4. Algebraic simplification— x+0, x-0, x*1, x/1, x*0, x**1, x**0, 0**x, 0*x
5. Unary minus folding     — -(-x) → x, -(literal) → literal
6. Comparison folding      — fold constant comparisons to True/False
7. Boolean folding         — fold constant logical ops
8. String concatenation    — fold constant string + string
9. Division-by-zero safety — never fold /0, //0, %0  (preserved as-is)

Safety rules
------------
- Never fold / // % with a zero divisor.
- Never produce non-finite floats from folding.
- Do not propagate a constant after the variable is reassigned.
- Multi-pass until the output stabilises (max 20 iterations).
- Preserve print instructions.
"""

from __future__ import annotations

import ast as _ast
import math
import operator
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Operator tables
# ---------------------------------------------------------------------------

_ARITH_OPS: dict[str, object] = {
    "+":  operator.add,
    "-":  operator.sub,
    "*":  operator.mul,
    "/":  operator.truediv,
    "//": operator.floordiv,
    "%":  operator.mod,
    "**": operator.pow,
}

_CMP_OPS: dict[str, object] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<":  operator.lt,
    "<=": operator.le,
    ">":  operator.gt,
    ">=": operator.ge,
}

_BOOL_AND = "and"
_BOOL_OR  = "or"
_BOOL_NOT = "not"


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_IDENT   = r"[A-Za-z_]\w*"
_INT_RE  = r"-?\d+"
_FLOAT_RE = r"-?(?:\d+\.\d*|\d*\.\d+)"
_STR_RE  = r"""(?:'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")"""
_BOOL_RE = r"True|False"

# A single operand (order matters: float before int, str, bool, ident)
_OPERAND = (
    rf"(?:{_STR_RE}|{_BOOL_RE}|{_FLOAT_RE}|{_INT_RE}|{_IDENT})"
)

_ASSIGN_RE = re.compile(
    rf"""^\s*({_IDENT})\s*=\s*(.+?)\s*$"""
)

# Arithmetic / comparison operators for binary patterns
_ARITH_AND_CMP_OPS = (
    r"//"   # must come before /
    r"|"
    r"\*\*" # must come before *
    r"|[+\-*/%]"
    r"|==|!=|<=|>=|<|>"
)

_BINARY_RE = re.compile(
    rf"""^\s*({_OPERAND})\s*({_ARITH_AND_CMP_OPS})\s*({_OPERAND})\s*$"""
)

_LOGICAL_AND_RE = re.compile(
    rf"""^\s*({_OPERAND})\s+and\s+({_OPERAND})\s*$"""
)
_LOGICAL_OR_RE  = re.compile(
    rf"""^\s*({_OPERAND})\s+or\s+({_OPERAND})\s*$"""
)
_LOGICAL_NOT_RE = re.compile(
    rf"""^\s*not\s+({_OPERAND})\s*$"""
)
_UNARY_MINUS_RE = re.compile(
    rf"""^\s*-({_OPERAND})\s*$"""
)
_COPY_RE = re.compile(
    rf"""^\s*({_IDENT})\s*$"""
)
_IDENT_RE = re.compile(rf"^{_IDENT}$")


# ---------------------------------------------------------------------------
# Literal helpers
# ---------------------------------------------------------------------------

def _parse_literal(text: str) -> tuple[object, bool]:
    """
    Safely parse text as a Python literal.
    Returns (value, True) on success or (None, False) on failure.
    """
    try:
        result = _ast.literal_eval(text.strip())
    except (ValueError, SyntaxError):
        return None, False

    if isinstance(result, (int, float, str, bool)):
        return result, True
    return None, False


def _format_literal(value) -> str:
    return repr(value)


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ---------------------------------------------------------------------------
# Safe fold helpers
# ---------------------------------------------------------------------------

def _safe_fold_arith(left, op: str, right) -> tuple[object, bool]:
    """Fold an arithmetic or comparison binary operation safely."""
    if op in _ARITH_OPS:
        if not (_is_number(left) and _is_number(right)):
            # String concatenation
            if op == "+" and isinstance(left, str) and isinstance(right, str):
                return left + right, True
            return None, False

        # Guard against division / floor-division / modulo by zero
        if op in ("/", "//", "%") and right == 0:
            return None, False

        # Guard against huge exponent (would OOM / hang)
        if op == "**":
            if isinstance(right, (int, float)) and right > 1000:
                return None, False
            if isinstance(left, (int, float)) and left == 0 and _is_number(right) and right < 0:
                return None, False  # 0 ** negative → ZeroDivisionError

        try:
            result = _ARITH_OPS[op](left, right)
        except (ArithmeticError, OverflowError, TypeError, ValueError):
            return None, False

        if isinstance(result, float) and not math.isfinite(result):
            return None, False

        return result, True

    if op in _CMP_OPS:
        if type(left) == type(right) or (_is_number(left) and _is_number(right)):
            try:
                result = _CMP_OPS[op](left, right)
                return result, True
            except TypeError:
                return None, False

    return None, False


def _safe_fold_logical_and(left, right) -> tuple[object, bool]:
    if isinstance(left, bool) and isinstance(right, bool):
        return left and right, True
    return None, False


def _safe_fold_logical_or(left, right) -> tuple[object, bool]:
    if isinstance(left, bool) and isinstance(right, bool):
        return left or right, True
    return None, False


def _safe_fold_logical_not(operand) -> tuple[object, bool]:
    if isinstance(operand, bool):
        return not operand, True
    return None, False


# ---------------------------------------------------------------------------
# Algebraic simplification (returns simplified expression text or None)
# ---------------------------------------------------------------------------

def _algebraic_simplify(left_text: str, op: str, right_text: str) -> Optional[str]:
    """
    Apply algebraic identities.  Returns a replacement expression string or None.
    Only applies when at least one side is a known literal.
    """
    left_val, left_is_lit  = _parse_literal(left_text)
    right_val, right_is_lit = _parse_literal(right_text)

    if op == "+":
        if right_is_lit and right_val == 0 and _is_number(right_val):
            return left_text          # x + 0 → x
        if left_is_lit and left_val == 0 and _is_number(left_val):
            return right_text         # 0 + x → x

    if op == "-":
        if right_is_lit and right_val == 0 and _is_number(right_val):
            return left_text          # x - 0 → x

    if op == "*":
        if right_is_lit and right_val == 1 and _is_number(right_val):
            return left_text          # x * 1 → x
        if left_is_lit and left_val == 1 and _is_number(left_val):
            return right_text         # 1 * x → x
        if right_is_lit and right_val == 0 and _is_number(right_val):
            return "0"                # x * 0 → 0
        if left_is_lit and left_val == 0 and _is_number(left_val):
            return "0"                # 0 * x → 0

    if op == "/":
        if right_is_lit and right_val == 1 and _is_number(right_val):
            return left_text          # x / 1 → x  (still float but eliminates temp)

    if op == "**":
        if right_is_lit and right_val == 1 and _is_number(right_val):
            return left_text          # x ** 1 → x
        if right_is_lit and right_val == 0 and _is_number(right_val):
            return "1"                # x ** 0 → 1
        if left_is_lit and left_val == 1 and _is_number(left_val):
            return "1"                # 1 ** x → 1
        if left_is_lit and left_val == 0 and _is_number(left_val):
            # 0 ** 0 is 1 in Python; 0 ** negative raises error — skip
            if right_is_lit and _is_number(right_val) and right_val > 0:
                return "0"            # 0 ** positive → 0

    return None


# ---------------------------------------------------------------------------
# Main optimizer class
# ---------------------------------------------------------------------------

class TACOptimizer:
    def __init__(self) -> None:
        self.optimization_log: list[str] = []

    def optimize(self, instructions: list[str]) -> list[str]:
        """
        Run optimization passes on *instructions* until stable.
        Returns the optimized instruction list.
        """
        self.optimization_log = []
        prev: list[str] = []
        current = [line for line in instructions if line.strip()]
        iterations = 0

        while current != prev and iterations < 20:
            prev = current
            current = self._single_pass(current)
            iterations += 1

        return current

    # ------------------------------------------------------------------
    # Single optimization pass
    # ------------------------------------------------------------------

    def _single_pass(self, instructions: list[str]) -> list[str]:
        constants: dict[str, object] = {}   # var → known constant
        copies: dict[str, str] = {}          # var → another variable name
        optimized: list[str] = []

        for instruction in instructions:
            line = instruction.strip()
            if not line:
                continue

            # ---- print statement -----------------------------------------
            if line.startswith("print "):
                operand = line[len("print "):].strip()
                operand = self._resolve(operand, constants, copies)
                optimized.append(f"print {operand}")
                continue

            # ---- assignment: target = <expression> ----------------------
            m = _ASSIGN_RE.fullmatch(line)
            if not m:
                optimized.append(line)
                continue

            target, expression = m.group(1), m.group(2).strip()

            # Invalidate stale knowledge BEFORE processing this instruction
            constants.pop(target, None)
            copies.pop(target, None)
            # Also remove entries that copied FROM target
            copies = {k: v for k, v in copies.items() if v != target}

            new_expr = self._optimize_expression(
                expression, target, constants, copies
            )

            optimized.append(f"{target} = {new_expr}")

        return optimized

    # ------------------------------------------------------------------
    # Expression-level optimization
    # ------------------------------------------------------------------

    def _optimize_expression(
        self,
        expression: str,
        target: str,
        constants: dict,
        copies: dict,
    ) -> str:
        """Optimize a single RHS expression; update constants/copies tables."""

        # --- try binary / compare op ---
        m = _BINARY_RE.fullmatch(expression)
        if m:
            return self._handle_binary(m, target, constants, copies)

        # --- try logical and ---
        m = _LOGICAL_AND_RE.fullmatch(expression)
        if m:
            left_t = self._resolve(m.group(1), constants, copies)
            right_t = self._resolve(m.group(2), constants, copies)
            lv, lc = _parse_literal(left_t)
            rv, rc = _parse_literal(right_t)
            if lc and rc:
                result, ok = _safe_fold_logical_and(lv, rv)
                if ok:
                    expr = _format_literal(result)
                    constants[target] = result
                    self.optimization_log.append(
                        f"{target}: folded {left_t} and {right_t} → {expr}"
                    )
                    return expr
            return f"{left_t} and {right_t}"

        # --- try logical or ---
        m = _LOGICAL_OR_RE.fullmatch(expression)
        if m:
            left_t = self._resolve(m.group(1), constants, copies)
            right_t = self._resolve(m.group(2), constants, copies)
            lv, lc = _parse_literal(left_t)
            rv, rc = _parse_literal(right_t)
            if lc and rc:
                result, ok = _safe_fold_logical_or(lv, rv)
                if ok:
                    expr = _format_literal(result)
                    constants[target] = result
                    self.optimization_log.append(
                        f"{target}: folded {left_t} or {right_t} → {expr}"
                    )
                    return expr
            return f"{left_t} or {right_t}"

        # --- try logical not ---
        m = _LOGICAL_NOT_RE.fullmatch(expression)
        if m:
            operand_t = self._resolve(m.group(1), constants, copies)
            ov, oc = _parse_literal(operand_t)
            if oc:
                result, ok = _safe_fold_logical_not(ov)
                if ok:
                    expr = _format_literal(result)
                    constants[target] = result
                    self.optimization_log.append(
                        f"{target}: folded not {operand_t} → {expr}"
                    )
                    return expr
            return f"not {operand_t}"

        # --- try unary minus ---
        m = _UNARY_MINUS_RE.fullmatch(expression)
        if m:
            operand_t = self._resolve(m.group(1), constants, copies)
            ov, oc = _parse_literal(operand_t)
            if oc and _is_number(ov):
                result = -ov
                expr = _format_literal(result)
                constants[target] = result
                self.optimization_log.append(
                    f"{target}: folded -{operand_t} → {expr}"
                )
                return expr
            return f"-{operand_t}"

        # --- simple copy / literal assignment ---
        resolved = self._resolve(expression, constants, copies)

        val, is_lit = _parse_literal(resolved)
        if is_lit:
            constants[target] = val
        elif _IDENT_RE.fullmatch(resolved) and resolved != target:
            # Copy: target = some_var  → remember the source
            copies[target] = resolved

        if resolved != expression:
            self.optimization_log.append(
                f"{target}: propagated {expression!r} → {resolved!r}"
            )

        return resolved

    def _handle_binary(
        self,
        m,
        target: str,
        constants: dict,
        copies: dict,
    ) -> str:
        left_text = self._resolve(m.group(1), constants, copies)
        op        = m.group(2)
        right_text = self._resolve(m.group(3), constants, copies)

        # Algebraic simplification first (does not require both to be literal)
        simplified = _algebraic_simplify(left_text, op, right_text)
        if simplified is not None:
            val, is_lit = _parse_literal(simplified)
            if is_lit:
                constants[target] = val
            self.optimization_log.append(
                f"{target}: algebraic {left_text} {op} {right_text} → {simplified}"
            )
            return simplified

        # Constant folding
        lv, lc = _parse_literal(left_text)
        rv, rc = _parse_literal(right_text)

        if lc and rc:
            result, ok = _safe_fold_arith(lv, op, rv)
            if ok:
                expr = _format_literal(result)
                constants[target] = result
                self.optimization_log.append(
                    f"{target}: folded {left_text} {op} {right_text} → {expr}"
                )
                return expr

        return f"{left_text} {op} {right_text}"

    # ------------------------------------------------------------------
    # Resolve: constant propagation + copy propagation
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve(operand: str, constants: dict, copies: dict) -> str:
        operand = operand.strip()

        if _IDENT_RE.fullmatch(operand):
            # Follow copy chain (one level)
            if operand in constants:
                return _format_literal(constants[operand])
            if operand in copies:
                src = copies[operand]
                if src in constants:
                    return _format_literal(constants[src])
                return src

        return operand


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def optimize_tac(instructions: list[str]) -> list[str]:
    """Optimize *instructions* and return the optimized list."""
    return TACOptimizer().optimize(instructions)
