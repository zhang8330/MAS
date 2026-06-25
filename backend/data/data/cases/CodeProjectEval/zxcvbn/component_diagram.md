```mermaid
graph TB
    caller["调用方（前端/后端/CLI）"] --> entry["__init__.py\nzxcvbn()"]

    subgraph match_layer["模式匹配层"]
      matching["matching.py\n多模式匹配"]
      freq["frequency_lists.py\n词频词典"]
      graph["adjacency_graphs.py\n键盘邻接图"]
    end

    subgraph score_layer["评分估算层"]
      scoring["scoring.py\n猜测数动态规划"]
      timeest["time_estimates.py\n攻击时间与分值"]
    end

    subgraph feedback_layer["反馈层"]
      fb["feedback.py\n警告与建议"]
    end

    subgraph cli_layer["CLI 层"]
      main["__main__.py\ncli + JSONEncoder"]
    end

    entry --> matching
    matching --> freq
    matching --> graph
    entry --> scoring
    scoring --> matching
    entry --> timeest
    entry --> fb
    fb --> scoring

    main --> entry
```