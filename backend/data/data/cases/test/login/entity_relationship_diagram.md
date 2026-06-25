erDiagram
    USER_ACCOUNT {
         string user_id PK
         string username
         string password_hash
         string password_salt
         string status "ENUM: ACTIVE | LOCKED | DISABLED"
		 int failed_attempts
		 string last_login_channel
		 datetime last_login_at
		 datetime created_at
         datetime updated_at
}


