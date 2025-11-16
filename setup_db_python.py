"""
Database setup script using Python
Alternative to running setup_database.sql directly
"""

import sys

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def setup_database():
    """Set up the ANYON database"""

    print("[*] Setting up PostgreSQL database...")

    # Connect to default postgres database first
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="postgres"  # Default password, user might need to change
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("[OK] Connected to PostgreSQL")

        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='anyon_db'")
        exists = cursor.fetchone()

        if not exists:
            print("[*] Creating database 'anyon_db'...")
            cursor.execute("CREATE DATABASE anyon_db")
            print("[OK] Database created")
        else:
            print("[INFO] Database 'anyon_db' already exists")

        # Check if user exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='anyon_user'")
        user_exists = cursor.fetchone()

        if not user_exists:
            print("[*] Creating user 'anyon_user'...")
            cursor.execute("CREATE USER anyon_user WITH PASSWORD 'anyon_password_2025'")
            print("[OK] User created")
        else:
            print("[INFO] User 'anyon_user' already exists")

        # Grant privileges
        print("[*] Granting privileges...")
        cursor.execute("GRANT ALL PRIVILEGES ON DATABASE anyon_db TO anyon_user")

        cursor.close()
        conn.close()

        # Now connect to anyon_db to create schemas
        conn = psycopg2.connect(
            host="localhost",
            database="anyon_db",
            user="postgres",
            password="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("[*] Creating schemas...")

        # Create schemas
        cursor.execute("CREATE SCHEMA IF NOT EXISTS shared")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS design_agent")
        print("[OK] Schemas created")

        # Grant schema privileges
        print("[*] Granting schema privileges...")
        for schema in ['shared', 'design_agent', 'public']:
            cursor.execute(f"GRANT USAGE ON SCHEMA {schema} TO anyon_user")
            cursor.execute(f"GRANT CREATE ON SCHEMA {schema} TO anyon_user")
            cursor.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} TO anyon_user")
            cursor.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema} TO anyon_user")
            cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON TABLES TO anyon_user")
            cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON SEQUENCES TO anyon_user")

        print("[OK] All privileges granted")

        cursor.close()
        conn.close()

        print("\n" + "="*60)
        print("[SUCCESS] Database setup complete!")
        print("="*60)
        print("Database: anyon_db")
        print("User: anyon_user")
        print("Password: anyon_password_2025")
        print("Schemas: shared, design_agent, public")
        print("="*60)

        return True

    except psycopg2.OperationalError as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print("\n[TIP] Troubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check if password is 'postgres' (or update the script)")
        print("3. Make sure PostgreSQL is accessible on localhost:5432")
        return False
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)
