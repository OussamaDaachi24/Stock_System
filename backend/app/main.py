import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import Base, engine
from .routers.auth import admin_router, router as auth_router
from .routers.inventory import router as inventory_router
from .routers.products import router as products_router
from .routers.purchase_orders import router as purchase_orders_router
from .routers.receipts import router as receipts_router
from .routers.reservations import router as reservations_router
from .routers.returns import credit_router as credit_memos_router, router as returns_router
from .routers.suppliers import router as suppliers_router


logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","msg":"%(message)s"}')
logger = logging.getLogger("stock_system")


def create_app() -> FastAPI:
    app = FastAPI(title="Stock Management System", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "app://-"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Base.metadata.create_all(bind=engine)

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(products_router)
    app.include_router(inventory_router)
    app.include_router(suppliers_router)
    app.include_router(purchase_orders_router)
    app.include_router(receipts_router)
    app.include_router(returns_router)
    app.include_router(credit_memos_router)
    app.include_router(reservations_router)

    @app.get("/api/v1/health")
    def health():
        return {"status": "success", "data": {"service": "stock-system", "ok": True}}

    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(_: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "error": {"code": exc.status_code, "message": exc.detail}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": {"code": 400, "message": "Validation error", "details": exc.errors()},
            },
        )

    return app


app = create_app()
