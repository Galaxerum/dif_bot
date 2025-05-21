from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from web.routes import router

app = FastAPI()

app.include_router(router)