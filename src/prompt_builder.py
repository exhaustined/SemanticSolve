def build_prompt(base_code, a_code, b_code):
    return f"""
You are a smart code merge assistant.

Below is Java code from three branches:

Base version:
```java
{base_code}
{a_code}
{b_code}
Merge these versions into a single, valid Java program that preserves the intent of both A and B.

Only provide multiple merge candidates if there is more than one reasonable way to combine the changes.

Output:
    One or more fully merged code candidates.
    Don't add any explanation or comments, nothing other than code.
    Use ```java to wrap each candidate (if multiple)."""