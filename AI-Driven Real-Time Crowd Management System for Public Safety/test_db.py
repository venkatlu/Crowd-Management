#!/usr/bin/env python3
import asyncio
import aiosqlite
import sys
import os

# Add current directory to path
sys.path.append('.')

async def test_database():
    try:
        print("Testing direct aiosqlite connection...")
        conn = await aiosqlite.connect('crowd_management.db')
        print("✓ Direct connection successful")
        await conn.close()
        
        print("\nTesting database manager...")
        from database import db_manager
        await db_manager.connect()
        print("✓ Database manager connection successful")
        await db_manager.close()
        
        print("\nAll tests passed!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database())
