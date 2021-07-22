from database import engine, get_db
import model

model.Base.metadata.create_all(bind=engine)

db = get_db()

if __name__ == '__main__':
    print("Hello world!")


