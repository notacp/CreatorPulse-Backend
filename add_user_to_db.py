#!/usr/bin/env python3
"""
Add confirmed user to local database.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from datetime import time

async def add_user_to_db():
    """Add confirmed user to local database."""
    
    print("🔧 Adding user to local database...")
    
    # User details from Supabase
    user_id = "18dc28f7-d218-42c3-89ef-aef498706881"
    email = "test-confirmed@gmail.com"
    password = "TestPassword123!"
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if user already exists
            result = await db.execute(select(User).where(User.id == user_id))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"✅ User already exists in database: {email}")
                return True
            
            # Create user in our database
            user = User(
                id=user_id,
                email=email,
                password_hash=get_password_hash(password),
                timezone="UTC",
                delivery_time=time(8, 0, 0),
                active=True,
                email_verified=True
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            print(f"✅ User added to database: {email}")
            print(f"   ID: {user.id}")
            print(f"   Email verified: {user.email_verified}")
            print(f"   Active: {user.active}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding user to database: {e}")
            await db.rollback()
            return False

if __name__ == "__main__":
    asyncio.run(add_user_to_db())
