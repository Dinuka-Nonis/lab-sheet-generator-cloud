"""
Database models for Lab Sheet Generator
SQLite for PythonAnywhere (no plan upgrade needed!)
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
import os
import secrets
import hashlib

Base = declarative_base()

# Global engine and session factory
_engine = None
_SessionFactory = None


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    student_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    api_key = Column(String(100), unique=True, nullable=False, index=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    modules = relationship('Module', back_populates='user', cascade='all, delete-orphan')
    schedules = relationship('Schedule', back_populates='user', cascade='all, delete-orphan')
    generation_history = relationship('GenerationHistory', back_populates='user', cascade='all, delete-orphan')

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def generate_api_key():
        return f"sk_{secrets.token_urlsafe(32)}"

    def verify_password(self, password):
        return self.password_hash == self.hash_password(password)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modules_count': len(self.modules),
            'schedules_count': len(self.schedules)
        }


class Module(Base):
    __tablename__ = 'modules'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    code = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    template = Column(String(50), default='classic')
    sheet_type = Column(String(50), default='Practical')
    custom_sheet_type = Column(String(100))
    use_zero_padding = Column(Boolean, default=True)
    output_path = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='modules')
    schedules = relationship('Schedule', back_populates='module', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'template': self.template,
            'sheet_type': self.sheet_type,
            'custom_sheet_type': self.custom_sheet_type,
            'use_zero_padding': self.use_zero_padding,
            'output_path': self.output_path
        }


class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    module_id = Column(Integer, ForeignKey('modules.id'), nullable=False)

    day_of_week = Column(Integer, nullable=False)
    lab_time = Column(String(10), nullable=False)
    generate_before_minutes = Column(Integer, default=60)

    current_practical_number = Column(Integer, default=1)
    auto_increment = Column(Boolean, default=True)
    use_zero_padding = Column(Boolean, default=True)

    status = Column(String(20), default='active')
    skip_dates = Column(Text)
    repeat_mode = Column(Boolean, default=False)

    upload_to_onedrive = Column(Boolean, default=True)
    send_confirmation = Column(Boolean, default=True)

    last_email_sent = Column(DateTime)
    last_generated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='schedules')
    module = relationship('Module', back_populates='schedules')

    def get_day_name(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[self.day_of_week]

    def to_dict(self):
        return {
            'id': self.id,
            'module_code': self.module.code if self.module else None,
            'module_name': self.module.name if self.module else None,
            'day_of_week': self.day_of_week,
            'day_name': self.get_day_name(),
            'lab_time': self.lab_time,
            'generate_before_minutes': self.generate_before_minutes,
            'current_practical_number': self.current_practical_number,
            'auto_increment': self.auto_increment,
            'use_zero_padding': self.use_zero_padding,
            'status': self.status,
            'skip_dates': self.skip_dates,
            'repeat_mode': self.repeat_mode,
            'upload_to_onedrive': self.upload_to_onedrive,
            'send_confirmation': self.send_confirmation,
            'last_generated_at': self.last_generated_at.isoformat() if self.last_generated_at else None
        }


class GenerationHistory(Base):
    __tablename__ = 'generation_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    module_code = Column(String(50), nullable=False)
    practical_number = Column(Integer, nullable=False)
    filename = Column(String(500), nullable=False)

    generated_via = Column(String(50), default='email')
    onedrive_link = Column(String(500))
    email_sent = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='generation_history')

    def to_dict(self):
        return {
            'id': self.id,
            'module_code': self.module_code,
            'practical_number': self.practical_number,
            'filename': self.filename,
            'generated_via': self.generated_via,
            'onedrive_link': self.onedrive_link,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def _get_db_url():
    """Get database URL — defaults to SQLite (no setup needed!)."""
    url = os.getenv('DATABASE_URL', '')
    if not url:
        # Store the SQLite file in the project directory
        project_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_dir, 'labsheets.db')
        url = f'sqlite:///{db_path}'
    return url


def init_database():
    """Create all tables. Called once on startup."""
    global _engine, _SessionFactory

    url = _get_db_url()

    # SQLite needs check_same_thread=False for Flask multi-threading
    connect_args = {}
    if url.startswith('sqlite'):
        connect_args = {'check_same_thread': False}

    _engine = create_engine(
        url,
        connect_args=connect_args,
        pool_recycle=280,
        pool_pre_ping=True
    )

    Base.metadata.create_all(_engine)

    # scoped_session is thread-safe — one session per thread
    _SessionFactory = scoped_session(sessionmaker(bind=_engine))

    import logging
    logging.getLogger(__name__).info(f"Database ready: {url}")


def get_db_session():
    """Return a thread-safe database session."""
    global _engine, _SessionFactory

    if _SessionFactory is None:
        init_database()

    return _SessionFactory()
