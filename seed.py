"""Ensures database tables exist. Restaurants are created via Super Admin."""
from app.database import SessionLocal, engine, Base

Base.metadata.create_all(bind=engine)
print("Database ready. Create restaurants via Super Admin → + New Restaurant")
