import re

text = """
applications in digital production.

## References

- [1] Gpt-4o system card. 2024. 6
"""

ref_patterns = [
    r"(?:\n#+\s+References\s*\n)",
    r"(?:\n#+\s+REFERENCES\s*\n)",
]

search_start = 0
for p in ref_patterns:
    match = re.search(p, text[search_start:])
    if match:
        print(f"Matched: {match.group(0)}")
        text = text[:search_start + match.start()]
        break

print("Text after:")
print(repr(text))
