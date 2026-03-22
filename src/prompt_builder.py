import json
def build_cluster_prompt(cluster_sigs, conflicting_methods, full_base_code):
    """
    Builds a prompt for an interprocedural cluster of interacting methods.
    """
    
    # Build the string showing the conflicting versions of all methods in this cluster
    methods_context = ""
    for sig in cluster_sigs:
        methods_context += f"\n### METHOD: {sig} ###\n"
        methods_context += f"# <BASE>\n{conflicting_methods[sig]['base']}\n# </BASE>\n"
        methods_context += f"# <BRANCH_A>\n{conflicting_methods[sig]['A']}\n# </BRANCH_A>\n"
        methods_context += f"# <BRANCH_B>\n{conflicting_methods[sig]['B']}\n# </BRANCH_B>\n"

    return f"""You are an advanced automated code merging engine resolving an INTERPROCEDURAL semantic conflict.

We have identified a "Cluster" of methods that interact with each other (e.g., one calls the other). 
Because they interact, you MUST merge them together as a cohesive unit. If Branch A changed a method's signature, you must ensure the other methods in this cluster are updated to call it correctly.

Context (The Full Base Class for reference only - DO NOT output the whole class):
~~~java
{full_base_code}
~~~

Here are the conflicting versions of the methods in this cluster:
{methods_context}

CRITICAL DIRECTIVES:
1. Generate 2 or 3 distinct "Merge Candidates" (different logical strategies for resolving the conflict).
2. Separate each candidate using EXACTLY this line: // MERGE_CANDIDATE_SEPARATOR
3. Inside EACH candidate, you MUST provide the merged code for ALL methods in the cluster.
4. To allow our system to parse your output, you MUST wrap each method's code in XML tags using the exact signature provided.

OUTPUT FORMAT EXAMPLE:
<method name="MethodOne(int)">
public void MethodOne(int x) {{
    // merged code here
}}
</method>
<method name="MethodTwo(String)">
public void MethodTwo(String y) {{
    // merged code here
}}
</method>
// MERGE_CANDIDATE_SEPARATOR
<method name="MethodOne(int)">
...

Do not include any markdown, explanations, or text outside of the XML tags and separators.
"""
def build_prompt(base_code, a_code, b_code):
    return f"""You are an advanced automated code merging engine. Your sole purpose is to perform a three-way merge of Java code, identifying and resolving conflicts, especially semantic ones. You will be given a BASE version of a code file, and two modified versions, BRANCH_A and BRANCH_B.

Your task is to analyze the changes in both branches relative to the base and generate one or more valid "merge candidates". Each candidate must be a complete, syntactically correct Java file that logically integrates the changes from both branches.

Critical Directives & Constraints:

    Preserve Dependencies: The merged code MUST preserve all data flow and control flow dependencies introduced in both branches. The final logic must be a coherent synthesis of the intents from both BRANCH_A and BRANCH_B.

    Resolve Semantic Conflicts: Your primary goal is to resolve semantic conflicts. A semantic conflict is when code can be merged textually without issue, but the resulting logic is flawed, incomplete, or violates the intent of one of the branches. You must produce code that is semantically sound.

    No New Classes: Do NOT introduce any new classes, interfaces, or enums. All merged code must exist within the original class structure provided in the BASE.

    Multiple Candidates: If there is more than one valid and logical way to merge the changes, generate each distinct solution as a separate merge candidate. For example, if the order of new operations could be logically interchanged, provide a candidate for each order.

    Imports and Signatures: Ensure all necessary import statements from both branches are included and de-duplicated. If method signatures are modified, the merged version must be compatible with the logic from both branches.

    Code Only: The output MUST strictly contain only the merged Java code. Do not include any explanations, introductory text, markdown formatting, or any characters outside of the code and the official separator.

Output Format:

    Your entire output will be raw Java code.

    If you generate multiple merge candidates, you MUST separate them with the following exact line, and nothing else:
    // MERGE_CANDIDATE_SEPARATOR
Input Code:

{base_code}
# <BRANCH_A>

# </BRANCH_A>
{a_code}
# <BRANCH_B>
{b_code}
# </BRANCH_B>
"""

def build_method_prompt(method_signature, base_method, a_method, b_method, full_base_code):
    return f"""You are an advanced automated code merging engine. Your sole purpose is to perform a three-way merge of Java code, identifying and resolving conflicts, especially semantic ones. You will be given a BASE version of a code file, and two modified versions, BRANCH_A and BRANCH_B.. 
We are resolving a semantic conflict at the PROCEDURE level.

Your task is to merge the method: `{method_signature}`, analyze the changes in both branches relative to the base and generate one or more valid "merge candidates". Each candidate must be a complete, syntactically correct procedure that logically integrates the changes from both branches.

Context (The Full Base Class for reference only - DO NOT output the whole class):
~~~java
{full_base_code}
~~~

The Conflicting Method Versions:

# <BASE_METHOD>
{base_method}
# </BASE_METHOD>

# <BRANCH_A_METHOD>
{a_method}
# </BRANCH_A_METHOD>

# <BRANCH_B_METHOD>
{b_method}
# </BRANCH_B_METHOD>

Critical Directives & Constraints:
    
    Output ONLY the merged Java code for THIS specific method.

    Do not include the rest of the class.

    Preserve Dependencies: The merged code MUST preserve all data flow and control flow dependencies introduced in both branches. The final logic must be a coherent synthesis of the intents from both BRANCH_A and BRANCH_B.

    Resolve Semantic Conflicts: Your primary goal is to resolve semantic conflicts. A semantic conflict is when code can be merged textually without issue, but the resulting logic is flawed, incomplete, or violates the intent of one of the branches. You must produce code that is semantically sound.

    No New Classes: Do NOT introduce any new classes, interfaces, or enums. All merged code must exist within the original class structure provided in the BASE.

    Multiple Candidates: If there is more than one valid and logical way to merge the changes, generate each distinct solution as a separate merge candidate. For example, if the order of new operations could be logically interchanged, provide a candidate for each order.

    Signatures: If method signatures are modified, the merged version must be compatible with the logic from both branches.

    Code Only: The output MUST strictly contain only the merged Java code. Do not include any explanations, introductory text, markdown formatting, or any characters outside of the code and the official separator.

"""

def build_report_prompt(class_name, conflicting_methods, combo_logs, run_results):
    """
    Constructs a prompt asking the LLM to generate a developer-friendly report.
    """
    method_names = list(conflicting_methods.keys())
    
    prompt = f"""You are a Senior Staff Software Engineer analyzing the results of an automated interprocedural code merge for the class `{class_name}`.

Here is the data from the automated merge pipeline:

1. CONFLICTING METHODS RESOLVED:
{json.dumps(method_names, indent=2)}

2. PERMUTATIONS TESTED:
This shows which generated candidate versions were combined for each test run.
{json.dumps(combo_logs, indent=2)}

3. VALIDATION RESULTS:
This shows the compiler and static analysis output for each permutation.
{json.dumps(run_results, indent=2)}

YOUR TASK:
Write a clear, professional, and highly readable "Merge Resolution Report" for the developer. 
The report MUST include:
- Executive Summary: Did we find a successful merge?
- Method Breakdown: Briefly explain what was likely changed in the conflicting methods.
- The Winning Combination (if any): Identify which permutation passed and why it is semantically sound.
- Failure Analysis: Explain why the other combinations failed (reference the specific compiler/tooling errors provided in the results).
- Next Steps: Anything the developer should manually verify.

Keep the tone professional, objective, and developer-centric. Format the report cleanly using Markdown.
"""
    return prompt


# def build_prompt(base_code, a_code, b_code):
#     return f"""You are an advanced automated code merging engine. Your sole purpose is to perform a three-way merge of Java code, identifying and resolving conflicts, especially semantic ones. You will be given a BASE version of a code file, and two modified versions, BRANCH_A and BRANCH_B.

# Your task is to analyze the changes in both branches relative to the base and generate one or more valid "merge candidates". Each candidate must be a complete, syntactically correct Java file that logically integrates the changes from both branches.

# Critical Directives & Constraints:

#     Preserve Dependencies: The merged code MUST preserve all data flow and control flow dependencies introduced in both branches. The final logic must be a coherent synthesis of the intents from both BRANCH_A and BRANCH_B.

#     Resolve Semantic Conflicts: Your primary goal is to resolve semantic conflicts. A semantic conflict is when code can be merged textually without issue, but the resulting logic is flawed, incomplete, or violates the intent of one of the branches. You must produce code that is semantically sound.

#     No New Classes: Do NOT introduce any new classes, interfaces, or enums. All merged code must exist within the original class structure provided in the BASE.

#     Multiple Candidates: If there is more than one valid and logical way to merge the changes, generate each distinct solution as a separate merge candidate. For example, if the order of new operations could be logically interchanged, provide a candidate for each order.

#     Imports and Signatures: Ensure all necessary import statements from both branches are included and de-duplicated. If method signatures are modified, the merged version must be compatible with the logic from both branches.

#     Code Only: The output MUST strictly contain only the merged Java code. Do not include any explanations, introductory text, markdown formatting, or any characters outside of the code and the official separator.

# Output Format:

#     Your entire output will be raw Java code.

#     If you generate multiple merge candidates, you MUST separate them with the following exact line, and nothing else:
#     // MERGE_CANDIDATE_SEPARATOR
# Input Code:

# {base_code}
# # <BRANCH_A>

# # </BRANCH_A>
# {a_code}
# # <BRANCH_B>
# {b_code}
# # </BRANCH_B>
# """


# """
# You are a smart code merge assistant.

# Below is Java code from three branches:

# Base version:
# ```java
# {base_code}
# {a_code}
# {b_code}
# Merge these versions into a single, valid Java program that preserves the intent of both A and B.

# Provide multiple merge candidates if there is more than one reasonable way to combine the changes.

# Output:
#     One or more fully merged code candidates.
#     Don't add any explanation or comments, nothing other than code.
#     Use ```java to wrap each candidate (if multiple)."""