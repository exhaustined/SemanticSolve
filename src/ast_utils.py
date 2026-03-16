
import javalang

def get_method_body(code_string, start_line):
    #extract exact code
    lines = code_string.splitlines()
    start_idx = start_line - 1
    
    brace_count = 0
    method_str = []
    found_start = False
    
    for i in range(start_idx, len(lines)):
        line = lines[i]
        method_str.append(line)
        for char in line:
            if char == '{':
                brace_count += 1
                found_start = True
            elif char == '}':
                brace_count -= 1
                
        if found_start and brace_count == 0:
            break
            
    return "\n".join(method_str)

def extract_methods(java_code):
    """Returns a dictionary of { 'MethodName(Args)': 'Method Body Code' }"""
    try:
        tree = javalang.parse.parse(java_code)
    except Exception as e:
        print(f"[❌] AST Parse Error: {e}")
        return {}
        
    methods = {}
    for path, node in tree.filter(javalang.tree.MethodDeclaration):
        # make signature
        sig = f"{node.name}({','.join([p.type.name for p in node.parameters])})"
        print("Signature:",sig)
        if node.position:
            body = get_method_body(java_code, node.position.line)
            methods[sig] = body
            
    return methods

def find_conflicting_methods(base_code, a_code, b_code):
    """Compares AST extractions to find which methods changed in both branches."""
    base_methods = extract_methods(base_code)
    a_methods = extract_methods(a_code)
    b_methods = extract_methods(b_code)
    
    conflicts = {}
    
    # Check for methods that exist in all 3 but differ in A and B relative to Base
    for sig, base_body in base_methods.items():
        if sig in a_methods and sig in b_methods:
            a_body = a_methods[sig]
            b_body = b_methods[sig]
            
            # both branches changed
            if a_body != base_body and b_body != base_body and a_body != b_body:
                conflicts[sig] = {
                    "base": base_body,
                    "A": a_body,
                    "B": b_body
                }
    return conflicts

def get_method_name(sig):
    # Extracts "calculateTotal" from "calculateTotal(int,int)"
    return sig.split('(')[0].strip()

def get_method_calls(java_code_string):
    """
    Parses a snippet of Java code and returns a set of all method names 
    that are called (invoked) within it.
    """
    calls = set()
    try:
        # We wrap the snippet in a dummy class/method so javalang can parse it as valid Java
        dummy_code = f"class Dummy {{ void dummyMethod() {{ {java_code_string} }} }}"
        tree = javalang.parse.parse(dummy_code)
        
        for path, node in tree.filter(javalang.tree.MethodInvocation):
            calls.add(node.member) # 'member' is the name of the method being called
            
    except Exception as e:
        # If parsing fails, return empty set
        pass
        
    return calls