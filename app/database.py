import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

if os.getenv("ABSOLUTE_DATABASE_LOCATION") is not None:
    SQLALCHEMY_DATABASE_URL = "sqlite:///" + os.getenv("ABSOLUTE_DATABASE_LOCATION")

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
