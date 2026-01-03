import os
from pymongo import MongoClient
import certifi

# User provided connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://himadric_db_user:rJgsq6hxSLWP6YBx@cluster0.e1osub8.mongodb.net/")
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
