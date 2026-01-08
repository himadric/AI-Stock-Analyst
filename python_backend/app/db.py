import os
from pymongo import MongoClient
import certifi

# User provided connection string
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("Warning: MONGO_URI not set in environment or .env file")
DB_NAME = "ai_stock_analyst"

class Database:
    client: MongoClient = None

    def connect(self):
        if not self.client:
            # use certifi for SSL certificates if needed on Mac
            self.client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
            print(f"Connected to MongoDB: {DB_NAME}")

    def get_db(self):
        if not self.client:
            self.connect()
        return self.client[DB_NAME]

db = Database()
