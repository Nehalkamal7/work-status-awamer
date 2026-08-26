from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
from app.api.integrations import router as integrations_router
from app.core.config import get_settings
from app.core.database import Base, engine

s=get_settings(); app=FastAPI(title=s.app_name,version="1.0.0",docs_url="/docs",redoc_url="/redoc")
app.add_middleware(CORSMiddleware,allow_origins=list({s.frontend_url,"http://localhost:3100","http://127.0.0.1:3100"}),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router); app.include_router(integrations_router)
@app.on_event("startup")
def startup():
    if s.environment=="development": Base.metadata.create_all(engine)
@app.get("/health")
def health(): return {"status":"healthy","service":s.app_name}
