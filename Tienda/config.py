import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    STORE_NAME = os.getenv("STORE_NAME", "Tienda")
    STORE_RUC = os.getenv("STORE_RUC", "")
    STORE_ADDRESS = os.getenv("STORE_ADDRESS", "")
    STORE_PHONE = os.getenv("STORE_PHONE", "")
    TAX_RATE = float(os.getenv("TAX_RATE", "0.15"))
