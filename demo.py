
from compiler.parser import parse_source
from compiler.semantic import analyze_ast
from compiler.tac import generate_tac
from compiler.optimizer import optimize_tac
source_code = """ 
x = 10 + 20 * 3
print(x)
"""

# Step 1: Parse the source code
ast, syntax_errors = parse_source(source_code)

print("\n========== SOURCE CODE ==========")
print(source_code)

print("\n========== THREE-ADDRESS CODE ==========")

if not syntax_errors and ast is not None:
    tac = generate_tac(ast)

    for instruction in tac:
        print(instruction)

print("\n========== OPTIMIZED TAC ==========")

optimized_tac = optimize_tac(tac)

for instruction in optimized_tac:
    print(instruction)

print("========== SYNTAX DIAGNOSTICS ==========")
if syntax_errors:
    for error in syntax_errors:
        print(error)
else:
    print("No syntax errors found.")

# Step 2: Run semantic analysis only if parsing succeeded
if not syntax_errors and ast is not None:
    symbols, diagnostics = analyze_ast(ast)

    print("\n========== SYMBOL TABLE ==========")
    for name, details in symbols.items():
        print(f"{name}: {details}")

    print("\n========== SEMANTIC DIAGNOSTICS ==========")
    if diagnostics:
        for item in diagnostics:
            print(
                f"{item['severity']} "
                f"(Line {item['line']}): {item['message']}"
            )
    else:
        print("No semantic issues found.")

