```mermaid
graph TD
    P1["chakin/downloader.py"]
    P2["chakin/__init__.py"]
    P3["unit_tests"]
    P4["acceptance_tests"]

    P2 --> P1
    P3 --> P1
    P4 --> P1
```