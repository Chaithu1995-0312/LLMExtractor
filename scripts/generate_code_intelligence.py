
import os
import ast
import json
import re
from collections import defaultdict

def determine_risk_profile(method_node, file_content):
    risk = "LOW: Pure/Safe"
    method_source = ast.get_source_segment(file_content, method_node)

    if method_source:
        # High Risk: DB Write/External API
        if re.search(r'conn\.(commit|execute)|sqlite3\.(connect|Cursor)|openai\.(ChatCompletion|Completion)', method_source):
            risk = "HIGH: DB Write/External API"
        # Med Risk: Local State/Disk
        elif re.search(r'open\(|os\.(path|remove|makedirs)|json\.(dump|load)|urllib\.request', method_source):
            if risk == "LOW: Pure/Safe": # Don\'t downgrade from High
                risk = "MED: Local State/Disk"
    return risk

def determine_idempotency(method_node, file_content):
    # Basic heuristic for now: assume idempotent if no obvious side effects or uses \'upsert\' patterns
    method_source = ast.get_source_segment(file_content, method_node)
    if method_source:
        if re.search(r'INSERT OR IGNORE|UPDATE.+WHERE|SELECT.+FOR UPDATE', method_source):
            return "✅ Yes"
        if "DELETE" in method_source or "create" in method_source.lower() and "idempotent" not in method_source.lower():
            return "❌ No"
    return "🟡 Partial"

def determine_state_impact(method_node, file_content):
    method_source = ast.get_source_segment(file_content, method_node)
    if method_source:
        if re.search(r'self\.\w+\s*=|self\[\w+\]\s*=|global\s+\w+', method_source):
            return "Mutates instance/global state"
    return "No direct state mutation detected"

def determine_validation_invariants(method_node, file_content):
    method_source = ast.get_source_segment(file_content, method_node)
    invariants = []
    if method_source:
        if "if not " in method_source:
            invariants.append("Input validation (e.g., \'if not x\')")
        if "assert " in method_source:
            invariants.append("Assertion checks")
        if "try:" in method_source and "except" in method_source:
            invariants.append("Error handling / exception-based invariants")
        if "raise ValueError" in method_source or "raise RuntimeError" in method_source:
            invariants.append("Explicit error raising for invalid states")
    return invariants if invariants else ["🔴 MISSING_FROM_CONTEXT"]

class CallCollector(ast.NodeVisitor):
    def __init__(self):
        self.calls = set()

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            # e.g., self.method(), obj.method()
            if isinstance(node.func.value, ast.Name):
                self.calls.add(node.func.attr)
            elif isinstance(node.func.value, ast.Call):
                # Handle chained calls like obj.get().method()
                pass # Too complex for initial pass
        elif isinstance(node.func, ast.Name):
            # e.g., function()
            self.calls.add(node.func.id)
        self.generic_visit(node)

def analyze_python_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    tree = ast.parse(content)
    classes_info = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            methods = {}
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_node = item
                    method_name = method_node.name
                    docstring = ast.get_docstring(method_node)
                    
                    # Basic Responsibility and Inputs/Outputs from docstring
                    responsibility = docstring.split("\n")[0].strip() if docstring else "🔴 MISSING_FROM_CONTEXT"
                    inputs_outputs = "🔴 MISSING_FROM_CONTEXT"
                    if docstring:
                        for line in docstring.split("\n"):
                            if "Args:" in line or "Returns:" in line or "Yields:" in line:
                                inputs_outputs = docstring # For now, take whole docstring
                                break

                    # Enhanced analysis
                    risk_profile = determine_risk_profile(method_node, content)
                    idempotency = determine_idempotency(method_node, content)
                    state_impact = determine_state_impact(method_node, content)
                    validation_invariants = determine_validation_invariants(method_node, content)
                    
                    # Collect method calls within this method
                    collector = CallCollector()
                    collector.visit(method_node)
                    
                    methods[method_name] = {
                        "responsibility": responsibility,
                        "risk_profile": risk_profile,
                        "inputs_outputs": inputs_outputs,
                        "idempotency": idempotency,
                        "state_impact": state_impact,
                        "validation_invariants": validation_invariants,
                        "calls": list(collector.calls)
                    }
            classes_info[class_name] = methods
            
    return classes_info

def main():
    base_dirs = ["src/nexus/", "services/cortex/"]
    all_files_info = {}
    
    for base_dir in base_dirs:
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith(("__", "test_")):
                    filepath = os.path.join(root, file)
                    # print(f"Analyzing {filepath}...") # Commented for cleaner output
                    file_classes_info = analyze_python_file(filepath)
                    if file_classes_info:
                        all_files_info[filepath] = file_classes_info
                        
    # Output to a JSON file for later processing
    with open("code_intelligence.json", "w", encoding="utf-8") as f:
        json.dump(all_files_info, f, indent=2)
        
    print("Code intelligence extracted to code_intelligence.json")

if __name__ == "__main__":
    main()
