from apihandler import APIHandler
from database import engine, SessionLocal
from model import Instance, Base

Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    db_session = SessionLocal()

    instance = db_session.query(Instance).first()

    handler = APIHandler(db_session, "https://applifting-python-excercise-ms.herokuapp.com/api/v1") # TODO: Get url from env

    if instance is None:
        handler.start()
    else:
        handler.start(instance.access_token)
