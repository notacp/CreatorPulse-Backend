#!/usr/bin/env python3
"""
Clean up test users from local database
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def cleanup_test_users():
    """Remove test users from local database"""
    
    print("🧹 Cleaning up test users from local database")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Find test users
        result = await db.execute(
            select(User).where(User.email.like("testuser%@gmail.com"))
        )
        users = result.scalars().all()
        
        print(f"Found {len(users)} test users:")
        for user in users:
            print(f"  - {user.email} (ID: {user.id})")
        
        if users:
            # Delete test users
            await db.execute(
                delete(User).where(User.email.like("testuser%@gmail.com"))
            )
            await db.commit()
            print(f"✅ Deleted {len(users)} test users")
        else:
            print("No test users found")

if __name__ == "__main__":
    asyncio.run(cleanup_test_users())
