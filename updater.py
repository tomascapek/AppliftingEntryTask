from apihandler import APIHandler

from database import engine, SessionLocal
from model import Instance, Base

Base.metadata.create_all(bind=engine)

db_session = SessionLocal()

handler = APIHandler(db_session, "https://applifting-python-excercise-ms.herokuapp.com/api/v1") # TODO: Get url from env


instance = db_session.query(Instance).first()
if instance is None:  # first time start
    handler.start()
else:  # we already have a access token
    handler.start(instance.access_token)

handler.update_offers()

