from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user_model import UserPreference

router = APIRouter(prefix="/user", tags=["User"])

@router.post("/set-language")
async def set_user_language(user_data: dict, db: Session = Depends(get_db)):
    user_pref = db.query(UserPreference).filter_by(user_id=user_data["user_id"]).first()
    
    if user_pref:
        user_pref.preferred_language = user_data["preferred_language"]
    else:
        user_pref = UserPreference(
            user_id=user_data["user_id"],
            preferred_language=user_data["preferred_language"]
        )
        db.add(user_pref)
    
    db.commit()
    return {"message": "Language preference updated"}

@router.get("/language/{user_id}")
async def get_user_language(user_id: str, db: Session = Depends(get_db)):
    user_pref = db.query(UserPreference).filter_by(user_id=user_id).first()
    return {"preferred_language": user_pref.preferred_language if user_pref else "en"}