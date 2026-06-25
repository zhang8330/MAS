[
  {
    "use_case_name": "从文本中抽取国家、城市与国籍信息",
    "primary_actor": "开发者/调用方",
    "secondary_actor": [
      "地理词典数据文件（countries/cities/nationalities）"
    ],
    "trigger": "调用方创建 GeoText(text, country=None) 实例",
    "use_case_description": "系统通过正则提取候选词，并基于预加载索引识别 countries、cities、nationalities，最终汇总 country_mentions 计数。",
    "preconditions": [
      "geotext/data_file 下的 nationalities.txt、countryInfo.txt、cities15000.txt、citypatches.txt 可读取",
      "输入文本为字符串"
    ],
    "postconditions": [
      "GeoText.countries、GeoText.cities、GeoText.nationalities 完成填充",
      "GeoText.country_mentions 为按出现次数排序的 OrderedDict"
    ],
    "main_flow": [
      "1. 调用方传入文本并执行 GeoText.__init__(text, country)",
      "2. 系统用正则表达式提取候选地名词",
      "3. 系统按索引匹配并区分国家、城市、国籍",
      "4. 若指定 country 参数，则按国家码过滤城市列表",
      "5. 系统聚合并统计 country_mentions"
    ],
    "alternative_flows": [
      "A1：当文本中无候选地名时，countries/cities/nationalities 为空列表。"
    ],
    "exception_flows": [
      "E1：数据文件缺失或格式异常时，索引构建失败并抛出异常。",
      "E2：文件读取编码错误时抛出 I/O 相关异常。"
    ],
    "priority": "High",
    "business_rules": [
      "国家名不会重复计入城市列表",
      "citypatches.txt 会覆盖城市索引中的同名项",
      "country_mentions 统计来源于国家名、城市映射国家码、国籍映射国家码"
    ],
    "assumptions": [
      "输入文本中的地名满足首字母大写等正则特征",
      "索引数据与测试中的期望国家码一致"
    ],
    "other_constraints": [
      "实现语言为 Python",
      "行为需覆盖 unit_tests 与 acceptance_tests"
    ]
  }
]
