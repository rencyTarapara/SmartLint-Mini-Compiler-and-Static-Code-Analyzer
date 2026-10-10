
class TACGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_count = 0

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def generate(self, ast):
        self.instructions = []
        self.temp_count = 0

        if ast is None:
            return []

        for statement in ast:
            self.generate_statement(statement)

        return self.instructions.copy()

    def generate_statement(self, statement):
        statement_type = statement["type"]

        if statement_type == "assign":
            name = statement["name"]
            value = self.generate_expression(statement["value"])
            self.instructions.append(f"{name} = {value}")

        elif statement_type == "print":
            value = self.generate_expression(statement["value"])
            self.instructions.append(f"print {value}")

    def generate_expression(self, expression):
        expression_type = expression["type"]

        if expression_type == "number":
            return repr(expression["value"])

        if expression_type == "string":
            return repr(expression["value"])

        if expression_type == "boolean":
            return "True" if expression["value"] else "False"

        if expression_type == "name":
            return expression["value"]

        if expression_type == "unary":
            operand = self.generate_expression(expression["value"])
            temp = self.new_temp()
            self.instructions.append(f"{temp} = -{operand}")
            return temp

        if expression_type == "binary":
            left = self.generate_expression(expression["left"])
            right = self.generate_expression(expression["right"])

            temp = self.new_temp()
            operator = expression["operator"]

            self.instructions.append(
                f"{temp} = {left} {operator} {right}"
            )
            return temp

        raise ValueError(
            f"Unsupported expression type: {expression_type}"
        )


def generate_tac(ast):
    generator = TACGenerator()
    return generator.generate(ast)
