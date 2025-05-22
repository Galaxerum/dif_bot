from fastapi import FastAPI
from web.routes import router

app = FastAPI()

app.include_router(router)