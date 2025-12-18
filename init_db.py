#!/usr/bin/env python
"""
Startup script for Railway deployment
Initializes database tables before starting the app
"""

from models import init_db
import os

def initialize():
    """Initialize database on startup"""
    print("🔄 Initializing database...")
    
    # Check if DATABASE_URL is set
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print(f"✅ DATABASE_URL found")
        
        # Initialize database (create tables if they don't exist)
        try:
            init_db()
            print("✅ Database tables initialized")
        except Exception as e:
            print(f"❌ Database initialization error: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️  No DATABASE_URL found, using SQLite")
        init_db()
    
    print("✅ Startup complete!")

if __name__ == '__main__':
    initialize()
