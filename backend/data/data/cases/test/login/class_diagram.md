@startuml
skinparam classAttributeIconSize 0
skinparam shadowing false
skinparam packageStyle rectangle

package "entity" {

    enum AccountStatus {
        ACTIVE
        LOCKED
        DISABLED
    }

    class UserAccount {
        -userId: String
        -username: String
        -passwordHash: String
        -passwordSalt: String
        -status: AccountStatus
        -failedAttempts: Integer
        -lastLoginAt: LocalDateTime
        -lastLoginChannel: String
        -createdAt: LocalDateTime
        -updatedAt: LocalDateTime
    }
}

package "dao" {
    interface UserAccountDao {
        +findByUsername(username: String): UserAccount
        +findByUserId(userId: String): UserAccount
        +incrementFailedAttempts(userId: String): int
        +resetFailedAttempts(userId: String): int
        +lockUser(userId: String): int
        +updateLoginProfile(userId: String, channel: String): int
    }
}

package "pojo" {
    class LoginRequest {
        -username: String
        -password: String
    }

    class UserIdentity {
        -userId: String
        -status: AccountStatus
        +UserIdentity(userId: String, status: AccountStatus)
    }

    class AuthenticationResult {
        -success: boolean
        -message: String
        -userId: String
        -status: AccountStatus
        +AuthenticationResult(success: boolean, message: String, userId: String, status: AccountStatus)
    }

    class ApiResponse<T> {
        -code: int
        -message: String
        -data: T
        +ApiResponse(code: int, message: String, data: T)
    }
}

package "service" {
    interface AuthenticationService {
        +findUserIdentityByUsername(username: String): UserIdentity
        +checkAccountAvailable(userId: String): boolean
        +verifyPassword(userId: String, rawPassword: String): boolean
        +recordLoginFailure(userId: String): void
        +recordLoginSuccess(userId: String, channel: String): void
    }
}

package "service.impl" {
    class AuthenticationServiceImpl {
        -MAX_FAILED_ATTEMPTS: int = 5
        -userAccountDao: UserAccountDao
        +AuthenticationServiceImpl(userAccountDao: UserAccountDao)
        +findUserIdentityByUsername(username: String): UserIdentity
        +checkAccountAvailable(userId: String): boolean
        +verifyPassword(userId: String, rawPassword: String): boolean
        +recordLoginFailure(userId: String): void
        +recordLoginSuccess(userId: String, channel: String): void
    }
}

package "controller" {
    class AuthController {
        -authenticationService: AuthenticationService
        +AuthController(authenticationService: AuthenticationService)
        +login(request: LoginRequest): ResponseEntity<ApiResponse<AuthenticationResult>>
    }
}

AuthController --> AuthenticationService
AuthController --> LoginRequest
AuthController --> UserIdentity
AuthController --> "ApiResponse<AuthenticationResult>"

AuthenticationServiceImpl ..|> AuthenticationService
AuthenticationServiceImpl --> UserAccountDao
AuthenticationServiceImpl --> UserAccount
AuthenticationServiceImpl --> UserIdentity

UserAccountDao --> UserAccount

AuthenticationService --> UserIdentity

UserIdentity --> AccountStatus
AuthenticationResult --> AccountStatus

@enduml
