"""
Database Schemas for LearnMate

Each Pydantic model corresponds to a MongoDB collection with the
collection name set to the lowercase of the class name.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# User profile data
class Profile(BaseModel):
    username: str = Field("guest", description="Unique username")
    full_name: Optional[str] = Field(None, description="Full name")
    language: str = Field("en", description="Preferred language code")
    push_notifications: bool = Field(True, description="Receive push notifications")

# Course catalog
class Course(BaseModel):
    title: str = Field(..., description="Course title")
    subject: str = Field(..., description="Subject area e.g., Mathematics")
    description: Optional[str] = Field(None, description="Short description")

# Notes created by user
class Note(BaseModel):
    username: str = Field("guest", description="Owner username")
    title: str = Field(..., description="Note title")
    content: str = Field("", description="Note content")

# Daily practice tracking
class Practice(BaseModel):
    username: str = Field("guest", description="Username")
    date: str = Field(..., description="YYYY-MM-DD date string")
    status: str = Field("completed", description="Practice status")

# Quiz question and results
class QuizQuestion(BaseModel):
    subject: str = Field(..., description="Subject of the question")
    text: str = Field(..., description="Question text")
    options: List[str] = Field(..., min_length=2, description="Multiple choice options")
    correct_index: int = Field(..., ge=0, description="Index of correct option")

class QuizResult(BaseModel):
    username: str = Field("guest", description="Username")
    subject: str = Field(..., description="Subject of quiz")
    total: int = Field(..., ge=1)
    correct: int = Field(..., ge=0)
    created_at: Optional[datetime] = None

# Simple notifications
class Notification(BaseModel):
    username: str = Field("guest", description="Username to notify or 'guest'")
    message: str = Field(..., description="Notification message")
    kind: str = Field("info", description="Type of notification")
