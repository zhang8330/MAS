```mermaid
graph TD
    subgraph src_main_java
        P1["com/sohu/idcenter"]
    end

    subgraph src_test_java
        P2["com/sohu/idcenter (tests)"]
    end

    subgraph src_acceptanceTest_java
        P3["acceptancetest"]
    end

    P2 --> P1
    P3 --> P1
```