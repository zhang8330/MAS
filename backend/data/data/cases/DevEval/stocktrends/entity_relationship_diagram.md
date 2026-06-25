```plantuml
@startuml
' source_mode: source
skinparam linetype ortho
entity "stocktrends_task" as A {
  * id : string
}
entity "stocktrends_record" as B {
  * id : string
  --
  ref_id : string
}
A ||--o{ B : relates
@enduml
```
