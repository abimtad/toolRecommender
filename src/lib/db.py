from pymongo import MongoClient
from src.config.env import MONGO_URI, DB_NAME

# Create ONE global client (best practice)
client = MongoClient(MONGO_URI)

# Access your database
db = client[DB_NAME]


def get_collection(name: str):
    """Get any collection by name."""
    return db[name]


def main():
    get_collection("Memory")


if __name__ == "__main__":
    main()
