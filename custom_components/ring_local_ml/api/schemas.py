from pydantic import BaseModel
import datetime

class EventBase(BaseModel):
    timestamp: datetime.datetime
    camera_id: str
    event_type: str
    clip_path: str
    snapshot_path: str
    face_detected: bool
    duration: int

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: int

    class Config:
        orm_mode = True
