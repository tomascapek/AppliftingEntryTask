from database import engine, session
import model

model.Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    print("Hello world!")


