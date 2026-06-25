@startuml
skinparam packageStyle rectangle
skinparam shadowing false

package "controller" {
    class AuthController
}

package "service" {
    interface AuthenticationService
}

package "service.impl" {
    class AuthenticationServiceImpl
}

package "dao" {
    interface UserAccountDao
}

package "entity" {
    class UserAccount
    enum AccountStatus
}

package "pojo" {
    class LoginRequest
    class UserIdentity
    class AuthenticationResult
    class ApiResponse
}

controller --> service
controller --> pojo

service --> pojo

service.impl --> service
service.impl --> dao
service.impl --> entity
service.impl --> pojo

dao --> entity

@enduml