```mermaid
graph TD
    P1["query_arxiv.py"]
    P2["unit_tests"]
    P3["acceptance_tests"]

    P2 --> P1
    P3 --> P1
```