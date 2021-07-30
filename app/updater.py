import os

from apihandler import APIHandler

from database import engine, SessionLocal
from model import Instance, Base

Base.metadata.create_all(bind=engine)

db_session = SessionLocal()

api_url = os.getenv("APPLIFTING_API_URL")
if api_url is None:
    raise RuntimeError("No APPLIFTING_API_URL is set.")

handler = APIHandler(db_session, api_url)

instance = db_session.query(Instance).first()
if instance is None:  # first time start
    handler.start()
else:  # we already have a access token
    handler.start(instance.access_token)

handler.update_offers()
