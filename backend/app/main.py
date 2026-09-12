from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.access import router as access_router
from app.api.auth import router as auth_router
from app.api.catalog import admin_catalog_router, catalog_router, merchant_catalog_router
from app.api.commerce import customer_router, product_router
from app.api.health import router as health_router
from app.api.management import admin_management_router, merchant_management_router
from app.api.merchant import admin_router as admin_merchant_router
from app.api.merchant import merchant_router
from app.core.config import get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.backend_cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(access_router)
    application.include_router(merchant_router)
    application.include_router(admin_merchant_router)
    application.include_router(catalog_router)
    application.include_router(admin_catalog_router)
    application.include_router(merchant_catalog_router)
    application.include_router(product_router)
    application.include_router(customer_router)
    application.include_router(merchant_management_router)
    application.include_router(admin_management_router)
    return application


app = create_app()
