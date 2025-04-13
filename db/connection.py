from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

def database_connect():
    uri = "mongodb+srv://moiukh29:abcd@cluster0.rupqvbl.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

    client = MongoClient(uri, server_api=ServerApi('1'))

    # Ping to confirm connection
    try:
        client.admin.command('ping')
        print("Successfully connected to MongoDB Atlas!")
    except Exception as e:
        print("Connection failed:", e)

    return client["restaurant_db"] 


