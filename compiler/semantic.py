
class SemanticAnalyzer:
    def __init__(self, warn_type_changes=True):
        self.symbol_table = {}
        self.diagnostics = []
        self.warn_type_changes = warn_type_changes

    def report(self, severity, line, message):
        self.diagnostics.append({
            "severity": severity,
            "line": line,
            "message": message,
        })

    def analyze(self, ast):
        self.symbol_table = {}
        self.diagnostics = []

        if ast is not None:
            for statement in ast:
                self.check_statement(statement)

        return self.symbol_table, self.diagnostics

    def check_statement(self, statement):
        statement_type = statement["type"]
        line = statement.get("line", 1)

        if statement_type == "assign":
            name = statement["name"]
            value_type = self.infer_type(statement["value"])

            # Store the variable only if its value has a valid type.
            if value_type is not None:
                previous = self.symbol_table.get(name)

                if (
                    previous is not None
                    and previous["type"] != value_type
                    and self.warn_type_changes
                ):
                    self.report(
                        "WARNING",
                        line,
                        f"Variable '{name}' changes type from "
                        f"{previous['type']} to {value_type}",
                    )

                self.symbol_table[name] = {
                    "type": value_type,
                    "line": line,
                }

        elif statement_type == "print":
            self.infer_type(statement["value"])

    def infer_type(self, expression):
        expression_type = expression["type"]
        line = expression.get("line", 1)

        if expression_type == "number":
            if isinstance(expression["value"], float):
                return "float"
            return "int"

        if expression_type == "string":
            return "str"

        if expression_type == "boolean":
            return "bool"

        if expression_type == "name":
            name = expression["value"]

            if name not in self.symbol_table:
                self.report(
                    "ERROR",
                    line,
                    f"Variable '{name}' is used before it is defined",
                )
                return None

            return self.symbol_table[name]["type"]

        if expression_type == "unary":
            operand_type = self.infer_type(expression["value"])

            if operand_type is None:
                return None

            if operand_type not in ("int", "float"):
                self.report(
                    "ERROR",
                    line,
                    f"Unary '-' cannot be applied to {operand_type}",
                )
                return None

            return operand_type

        if expression_type == "binary":
            left_type = self.infer_type(expression["left"])
            right_type = self.infer_type(expression["right"])
            operator = expression["operator"]

            # Avoid duplicate type errors when an operand is undefined.
            if left_type is None or right_type is None:
                return None

            # String concatenation is allowed with +.
            if operator == "+" and left_type == right_type == "str":
                return "str"

            numeric_types = ("int", "float")

            if (
                left_type not in numeric_types
                or right_type not in numeric_types
            ):
                self.report(
                    "ERROR",
                    line,
                    f"Operator '{operator}' cannot be applied to "
                    f"{left_type} and {right_type}",
                )
                return None

            if operator == "/":
                return "float"

            if "float" in (left_type, right_type):
                return "float"

            return "int"

        return None


def analyze_ast(ast, warn_type_changes=True):
    analyzer = SemanticAnalyzer(
        warn_type_changes=warn_type_changes
    )
    return analyzer.analyze(ast)
