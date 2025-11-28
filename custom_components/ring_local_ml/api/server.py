from fastapi import FastAPI
from ..storage.db import get_session, Event

app = FastAPI()

@app.get("/events")
def get_events():
    session = get_session()
    events = session.query(Event).all()
    return events

@app.get("/events/{event_id}")
def get_event(event_id: int):
    session = get_session()
    event = session.query(Event).filter(Event.id == event_id).first()
    return event
