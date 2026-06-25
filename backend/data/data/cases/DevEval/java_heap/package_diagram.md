```mermaid
graph TD
    subgraph src_main_java
        P1["code"]
    end

    subgraph src_test_java
        P2["test"]
    end

    P2 --> P1
```