from fastapi import FastAPI

from db import engine
from model_base import Base

from operators.controller import router as operator_router
from leads.controller import router as lead_router
from contacts.controller import router as contact_router

# Create all tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/health")
def root():
    """Simple health check endpoint."""
    return {"status": "ok"}


app.include_router(operator_router)
app.include_router(lead_router)
app.include_router(contact_router)
