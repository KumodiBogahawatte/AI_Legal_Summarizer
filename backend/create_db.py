# backend/create_db.py
from app.db import engine, Base
from app.models import document_model, rights_violation_model  # imports ensure registration

def create_all():
    Base.metadata.create_all(bind=engine)
    print("SQLite DB and tables created.")

if __name__ == "__main__":
    create_all()
