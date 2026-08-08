from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from momentum.api.routes import health, workflows, opportunities, automations, events, privacy, learning


def create_app() -> FastAPI:
    app = FastAPI(
        title="MOMENTUM API",
        description="Local AI Developer Workflow Discovery Daemon",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(events.router, prefix="/api/v1", tags=["events"])
    app.include_router(workflows.router, prefix="/api/v1", tags=["workflows"])
    app.include_router(opportunities.router, prefix="/api/v1", tags=["opportunities"])
    app.include_router(automations.router, prefix="/api/v1", tags=["automations"])
    app.include_router(learning.router, prefix="/api/v1", tags=["learning"])
    app.include_router(privacy.router, prefix="/api/v1", tags=["privacy"])

    return app
