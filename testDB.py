#!/usr/bin/env python3

import os
import datetime
import pymongo
from dotenv import load_dotenv

load_dotenv()


def test_connection():
    """Test MongoDB connection by inserting and reading a document."""
    
    print("Connecting to MongoDB...")
    
    try:
        cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
        db = cxn[os.getenv("MONGO_DBNAME")]
        
        cxn.admin.command("ping")
        print("✓ Connected!")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    print("Inserting test document...")
    doc = {
        "name": "Test User",
        "message": "DB connection works!",
        "created_at": datetime.datetime.utcnow(),
    }
    result = db.test.insert_one(doc)
    print(f"✓ Inserted with ID: {result.inserted_id}")
    
    print("Reading back...")
    found = db.test.find_one({"_id": result.inserted_id})
    print(f"✓ Found: {found}")
    
    print("Cleaning up...")
    db.test.delete_one({"_id": result.inserted_id})
    print("✓ Deleted test document")
    
    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    test_connection()