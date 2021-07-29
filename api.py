from fastapi import FastAPI, Response, status

from apihandler import APIHandler, ProductAlreadyExists, ProductDoesntExist
from database import engine, SessionLocal
from model import Instance, Base
from pydantic_model import Product, UpdateProduct

Base.metadata.create_all(bind=engine)

api = FastAPI()

db_session = SessionLocal()

handler = APIHandler(db_session, "https://applifting-python-excercise-ms.herokuapp.com/api/v1") # TODO: Get url from env

instance = db_session.query(Instance).first()
if instance is None:  # first time start
    handler.start()
else:  # we already have a access token
    handler.start(instance.access_token)


@api.post("/create-product")
def create(product: Product, response: Response):
    try:
        handler.create_product(product.name, product.description)
        response.status_code = status.HTTP_201_CREATED
        return
    except ProductAlreadyExists:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "message": "This product already exist."
        }
    except RuntimeError:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


@api.get("/list-all")
def list_all():
    return handler.list_products()


@api.post("/change-product")
def change_product(product: UpdateProduct, response: Response):
    try:
        handler.update_product(product.product_id, product.name, product.description)
        response.status_code = status.HTTP_200_OK
    except ProductAlreadyExists:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "message": "Product with this name already exists."
        }
    except ProductDoesntExist:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "message": "Product with this ID doesn't exists."
        }


@api.delete("/delete-product/{product_id}")
def delete_product(product_id, response: Response):
    try:
        handler.delete_product(product_id)
    except ProductDoesntExist:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "message": "Product with this ID doesn't exists."
        }
