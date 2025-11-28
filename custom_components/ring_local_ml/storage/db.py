from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    camera_id = Column(String)
    event_type = Column(String) # "motion", "ding"
    clip_path = Column(String)
    snapshot_path = Column(String)
    face_detected = Column(Boolean)
    duration = Column(Integer)

def get_session(db_path='sqlite:///media.db'):
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    return DBSession()
