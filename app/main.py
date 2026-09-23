import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, authors, books, branches, copies, faculties, health, loans, reports

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("library")
app = FastAPI(title="Library API", version="0.1.0")
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(authors.router)
app.include_router(faculties.router)
app.include_router(branches.router)
app.include_router(books.router)
app.include_router(copies.router)
app.include_router(loans.router)
app.include_router(reports.router)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Необработанная ошибка при обработке запроса %s", request.url)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


@app.get("/")
def root():
    return {"service": "library-api", "version": "0.1.0", "docs": "/docs"}
