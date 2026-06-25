```mermaid
graph TD
    P1["src/hybrid.py"]
    P2["unit_tests"]
    P3["acceptance_tests"]
    P4["examples/demo.py"]

    P2 --> P1
    P3 --> P1
    P4 --> P1
```