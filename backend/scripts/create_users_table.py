#!/usr/bin/env python3
"""
Database migration script to create the users table and initial admin user
for the Vinci Automation secure authentication system.
"""

import os
from supabase import create_client, Client


def create_users_table(supabase: Client) -> bool:
    """
    Create the users table in Supabase if it doesn't exist.
    
    The table structure follows:
    - id: Primary key (UUID)
    - username: Unique, not null
    - email: Unique, not null
    - hashed_password: Not null
    - role: Role-based access (admin, user)
    - is_active: Boolean for account status
    - created_at: Timestamp when created
    - last_login: Timestamp of last successful login
    """
    try:
        # Check if table exists by trying to select from it
        response = supabase.table("users").select("id").limit(1).execute()
        if response.data:
            print("✓ 'users' table already exists")
            return True
    except Exception:
        pass
    
    # Define the table schema
    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        last_login TIMESTAMP WITH TIME ZONE
    );
    
    -- Create index for faster username lookups
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
    
    -- Set up RLS (Row Level Security)
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    
    -- Policy: Users can only access their own data, unless admin
    CREATE POLICY users_select_own ON users
        FOR SELECT USING (auth.uid() = id OR role = 'admin');
    
    CREATE POLICY users_insert_own ON users
        FOR INSERT WITH CHECK (auth.uid() = id OR role = 'admin');
    
    CREATE POLICY users_update_own ON users
        FOR UPDATE USING (auth.uid() = id OR role = 'admin');
    
    CREATE POLICY users_delete_own ON users
        FOR DELETE USING (auth.uid() = id OR role = 'admin');
    """
    
    try:
        supabase.rpc('exec_sql', {'sql': sql}).execute()
        print("✓ Created 'users' table successfully")
        return True
    except Exception as e:
        print(f"✗ Error creating users table: {e}")
        return False


def create_initial_admin_user(supabase: Client) -> bool:
    """
    Create the initial admin user if it doesn't exist.
    
    This should be done after the users table is created.
    """
    import os
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated=["auto"])
    
    # Get admin credentials from environment
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@vinciautomation.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    
    if not admin_password:
        print("✗ ADMIN_PASSWORD environment variable is required")
        return False
    
    # Check if admin user already exists
    existing_users = supabase.table("users").select("*").eq("username", admin_username).execute()
    if existing_users.data:
        print("✓ Admin user already exists")
        return True
    
    # Create admin user with hashed password
    hashed_password = pwd_context.hash(admin_password)
    admin_data = {
        "username": admin_username,
        "email": admin_email,
        "hashed_password": hashed_password,
        "role": "admin",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    try:
        result = supabase.table("users").insert(admin_data).execute()
        if result.data:
            print(f"✓ Created initial admin user: {admin_username}")
            print(f"  (Change password immediately: '{admin_password}' -> new secure password)")
            return True
        else:
            print("✗ Failed to create admin user")
            return False
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        return False


def main():
    """Main function to run the database migration."""
    print("=" * 60)
    print("Vinci Automation - Database Migration Script")
    print("=" * 60)
    
    # Load environment variables
    os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
    os.environ.setdefault("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODQ3OTU2MDAsImV4cCI6MTkxNjI1NzYwMH0.jS4m0rSfPoG5Rc5v8Vx6qNq6vZ5Wv5mRf5vXvXvXf5vP5v8Vx6qNq6vZ5Wv5mRf5")
    
    # Get Supabase URL and key from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("✗ SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        print("  Set them to your Supabase project URL and service_role key")
        return
    
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Run migrations
    if create_users_table(supabase):
        create_initial_admin_user(supabase)
    
    print("\n" + "=" * 60)
    print("Migration completed!")
    print("Next steps:")
    print("1. Set environment variables:")
    print("   export SUPABASE_URL='your-supabase-url'")
    print("   export SUPABASE_KEY='your-service-role-key'")
    print("   export ADMIN_PASSWORD='secure-admin-password'")
    print("   export JWT_SECRET_KEY='generate-a-secure-jwt-secret'")
    print("2. Run: python backend/app/main.py")
    print("3. Access auth API endpoints:")
    print("   POST /api/auth/register -> Create new users")
    print("   POST /api/auth/login -> Get JWT token")
    print("   GET /api/auth/me -> Get current user info")
    print("=" * 60)


if __name__ == "__main__":
    from datetime import datetime
    main()