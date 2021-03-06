import os

from fastapi import FastAPI, Response, status

from apihandler import APIHandler, ProductAlreadyExists, ProductDoesntExist
from database import engine, SessionLocal
from model import Instance, Base
from pydantic_model import Product, UpdateProduct, TimeRange

Base.metadata.create_all(bind=engine)

api = FastAPI(
    title="Offers microservice by Tomáš Čapek",
    description="This API was created as a part of the application process for Python Developer position in Applifting company.",
    version="1.0"
)

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


@api.post(
    "/create-product",
    name="Create new product",
    description="This endpoint is used to create new product."
)
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


@api.get(
    "/list-all",
    name="List all products and offers",
    description="This endpoint will list all the available products with their non-zero stocked offers."
)
def list_all():
    return handler.list_products()


@api.post(
    "/change-product",
    name="Edit product information",
    description="Change name or description of the given product."
)
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


@api.delete(
    "/delete-product/{product_id}",
    name="Remove product from the Offers microservice",
    description="Will remove given product from this service."
)
def delete_product(product_id, response: Response):
    try:
        handler.delete_product(product_id)
    except ProductDoesntExist:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "message": "Product with this ID doesn't exists."
        }


@api.post(
    "/product-offer-history/{product_id}",
    name="Get history of offers related to given product.",
    description="Returns history and rise or fall percentage for given product."
)
def product_offer_history(product_id: int, time_range: TimeRange, response: Response):
    try:
        return handler.get_history(product_id, time_range.start, time_range.end)
    except ProductDoesntExist:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "message": "Product with this ID doesn't exists."
        }
