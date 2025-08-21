#!/usr/bin/env python3
"""
Simple script to view registered users in the database
"""
import asyncio
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Database URL from environment or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

# Convert to async URL if needed
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("postgres://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

async def view_users():
    """View all users in the database"""
    try:
        # Create async engine
        engine = create_async_engine(ASYNC_DATABASE_URL)
        
        # Create async session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Query users
            result = await session.execute(
                text("SELECT id, email, timezone, delivery_time, active, email_verified, created_at FROM users ORDER BY created_at DESC LIMIT 20")
            )
            users = result.fetchall()
            
            print(f"\n📊 Users in Database ({len(users)} recent users):")
            print("=" * 80)
            
            if not users:
                print("No users found in database.")
                return
            
            # Print header
            print(f"{'Email':<30} {'ID':<36} {'Active':<7} {'Verified':<9} {'Created':<20}")
            print("-" * 80)
            
            # Print users
            for user in users:
                email = user[1][:29] if len(user[1]) > 29 else user[1]
                user_id = str(user[0])[:35] if len(str(user[0])) > 35 else str(user[0])
                active = "Yes" if user[4] else "No"
                verified = "Yes" if user[5] else "No"
                created = user[6].strftime("%Y-%m-%d %H:%M") if user[6] else "Unknown"
                
                print(f"{email:<30} {user_id:<36} {active:<7} {verified:<9} {created:<20}")
            
            print("\n" + "=" * 80)
            print(f"✅ Total users shown: {len(users)}")
            print("📝 Note: Users are stored in PostgreSQL, not Supabase")
            print("🔐 Authentication: Standalone JWT + bcrypt")
            
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print(f"🔍 Database URL: {ASYNC_DATABASE_URL[:50]}...")
        print("\n💡 Make sure you have the DATABASE_URL environment variable set")
        print("   or run this script on Render where the database is accessible")

if __name__ == "__main__":
    asyncio.run(view_users())
