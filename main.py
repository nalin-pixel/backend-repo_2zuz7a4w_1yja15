import os
from datetime import datetime, timezone, date
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Profile, Course, Note, Practice, QuizQuestion, QuizResult, Notification

app = FastAPI(title="LearnMate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "LearnMate Backend is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Seed some sample courses if none exist
@app.post("/seed")
def seed_data():
    existing = db["course"].count_documents({}) if db else 0
    if existing == 0 and db is not None:
        subjects = [
            ("Mathematics", "Mathematics"),
            ("Science", "Science"),
            ("English", "English"),
            ("Computer/ICT", "Computer/ICT"),
            ("Social Studies", "Social Studies"),
        ]
        for title, subject in subjects:
            create_document("course", Course(title=title, subject=subject, description=f"Intro to {subject}"))
        create_document("notification", Notification(message="New course added!"))
    return {"status": "ok"}

# Courses
@app.get("/courses", response_model=List[Course])
def list_courses():
    docs = get_documents("course")
    # Remove _id for response model compatibility
    res = [{k: v for k, v in d.items() if k in Course.model_fields} for d in docs]
    return res

# Notes
class NoteCreate(BaseModel):
    title: str
    content: str
    username: Optional[str] = "guest"

@app.get("/notes", response_model=List[Note])
def get_notes(username: str = Query("guest")):
    docs = get_documents("note", {"username": username})
    res = [{k: v for k, v in d.items() if k in Note.model_fields} for d in docs]
    return res

@app.post("/notes")
def add_note(payload: NoteCreate):
    note = Note(username=payload.username or "guest", title=payload.title, content=payload.content)
    note_id = create_document("note", note)
    create_document("notification", Notification(message="New note saved"))
    return {"message": "Note saved successfully", "id": note_id}

@app.delete("/notes/{title}")
def delete_note(title: str, username: str = Query("guest")):
    if db is None:
        raise HTTPException(500, "Database not available")
    result = db["note"].delete_one({"username": username, "title": title})
    if result.deleted_count == 0:
        raise HTTPException(404, "Note not found")
    create_document("notification", Notification(message="Note deleted successfully"))
    return {"message": "Note deleted successfully"}

# Practice
@app.post("/practice/start")
def start_practice(username: str = "guest"):
    today = date.today().isoformat()
    if db is None:
        raise HTTPException(500, "Database not available")
    existing = db["practice"].find_one({"username": username, "date": today})
    if existing:
        return {"message": "You have completed today’s practice, try again tomorrow"}
    create_document("practice", Practice(username=username, date=today, status="completed"))
    create_document("notification", Notification(message="Start today’s practice"))
    return {"message": "Practice saved successfully"}

@app.get("/practice/history")
def practice_history(username: str = Query("guest")):
    docs = get_documents("practice", {"username": username})
    # just return minimal fields
    return [{"date": d.get("date"), "status": d.get("status") } for d in docs]

# Quiz
SAMPLE_QUESTIONS: List[QuizQuestion] = [
    QuizQuestion(subject="General", text="2 + 2 = ?", options=["3", "4", "5", "6"], correct_index=1),
    QuizQuestion(subject="General", text="Capital of France?", options=["Berlin", "Paris", "Madrid", "Rome"], correct_index=1),
]

class QuizAnswer(BaseModel):
    answers: List[int]
    subject: Optional[str] = "General"
    username: Optional[str] = "guest"

@app.get("/quiz/questions", response_model=List[QuizQuestion])
def get_quiz_questions(subject: str = Query("General")):
    # In a real app, fetch from DB. For now serve sample questions and also allow seeding DB later.
    return SAMPLE_QUESTIONS

@app.post("/quiz/submit")
def submit_quiz(payload: QuizAnswer):
    total = len(SAMPLE_QUESTIONS)
    correct = 0
    for i, q in enumerate(SAMPLE_QUESTIONS):
        ai = payload.answers[i] if i < len(payload.answers) else -1
        if ai == q.correct_index:
            correct += 1
    create_document("quizresult", QuizResult(username=payload.username or "guest", subject=payload.subject or "General", total=total, correct=correct, created_at=datetime.now(timezone.utc)))
    create_document("notification", Notification(message=f"Your quiz score: {correct}/{total}"))
    return {"message": "You have completed the quiz!", "correct": correct, "total": total}

# Profile & settings
class ProfileUpdate(BaseModel):
    username: Optional[str] = "guest"
    full_name: Optional[str] = None
    language: Optional[str] = None
    push_notifications: Optional[bool] = None

@app.get("/profile", response_model=Profile)
def get_profile(username: str = Query("guest")):
    if db is None:
        raise HTTPException(500, "Database not available")
    doc = db["profile"].find_one({"username": username})
    if not doc:
        # create default
        profile = Profile(username=username)
        create_document("profile", profile)
        return profile
    # return only model fields
    return Profile(**{k: v for k, v in doc.items() if k in Profile.model_fields})

@app.post("/profile")
def update_profile(payload: ProfileUpdate):
    if db is None:
        raise HTTPException(500, "Database not available")
    username = payload.username or "guest"
    update = {k: v for k, v in payload.model_dump().items() if v is not None and k != "username"}
    db["profile"].update_one({"username": username}, {"$set": update}, upsert=True)
    create_document("notification", Notification(message="Profile updated"))
    return {"message": "Saved successfully"}

# Notifications
@app.get("/notifications", response_model=List[Notification])
def get_notifications(username: str = Query("guest")):
    docs = get_documents("notification", {"$or": [{"username": username}, {"username": "guest"}]})
    res = [{k: v for k, v in d.items() if k in Notification.model_fields} for d in docs]
    return res

# General system messages endpoint for health/loading
@app.get("/health")
def health():
    return {"status": "ok", "message": "Loading…"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
