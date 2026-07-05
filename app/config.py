import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dineflow.db")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-production")
