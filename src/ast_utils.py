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
    """Returns a dictionary of { 'MethodName': {'sig': '...', 'body': '...'} }"""
    try:
        tree = javalang.parse.parse(java_code)
    except Exception as e:
        print(f"[❌] AST Parse Error: {e}")
        return {}
        
    methods = {}
    for path, node in tree.filter(javalang.tree.MethodDeclaration):
        # make signature
        sig = f"{node.name}({','.join([p.type.name for p in node.parameters])})"
        if node.position:
            body = get_method_body(java_code, node.position.line)
            methods[node.name] = {
                "sig": sig,
                "body": body
            }
            
    return methods

def find_conflicting_methods(base_code, a_code, b_code):
    """
    Finds any method that was modified (either body or signature) in Branch A OR Branch B.
    This creates the 'Topography Pool' for the Call-Graph to cluster.
    """
    base_methods = extract_methods(base_code)
    a_methods = extract_methods(a_code)
    b_methods = extract_methods(b_code)
    
    changed_methods = {}
    
    for name, base_data in base_methods.items():
        if name in a_methods and name in b_methods:
            a_data = a_methods[name]
            b_data = b_methods[name]
            
            base_body, base_sig = base_data["body"], base_data["sig"]
            a_body, a_sig = a_data["body"], a_data["sig"]
            b_body, b_sig = b_data["body"], b_data["sig"]
            
            a_changed = (a_body != base_body) or (a_sig != base_sig)
            b_changed = (b_body != base_body) or (b_sig != base_sig)
            
            if a_changed or b_changed:
                changed_methods[base_sig] = {
                    "base": base_body,
                    "A": a_body,
                    "B": b_body
                }
                
    return changed_methods

def get_method_calls(java_code_string):
    """
    Parses a snippet of Java code and returns a set of all method names 
    that are called (invoked) within it. Used for Call-Graph clustering.
    """
    calls = set()
    try:
        dummy_code = f"class Dummy {{\n{java_code_string}\n}}"
        tree = javalang.parse.parse(dummy_code)
        
        for path, node in tree.filter(javalang.tree.MethodInvocation):
            calls.add(node.member) # 'member' is the name of the method being called
            
    except Exception as e:
        # print(f"Parse error in get_method_calls: {e}")
        pass
        
    return calls
def get_method_name(sig):
    # Extracts "calculateTotal" from "calculateTotal(int,int)"
    return sig.split('(')[0].strip()