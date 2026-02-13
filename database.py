"""
Database models for multi-user Lab Sheet Generator
PostgreSQL with SQLAlchemy
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
import secrets
import hashlib

Base = declarative_base()


class User(Base):
    """User model for authentication and profile."""
    
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
    
    # Relationships
    modules = relationship('Module', back_populates='user', cascade='all, delete-orphan')
    schedules = relationship('Schedule', back_populates='user', cascade='all, delete-orphan')
    generation_history = relationship('GenerationHistory', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User {self.student_id} - {self.name}>"
    
    @staticmethod
    def hash_password(password):
        """Hash password with SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def generate_api_key():
        """Generate secure API key."""
        return f"sk_{secrets.token_urlsafe(32)}"
    
    def verify_password(self, password):
        """Verify password against hash."""
        return self.password_hash == self.hash_password(password)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'modules_count': len(self.modules),
            'schedules_count': len(self.schedules)
        }


class Module(Base):
    """Module/Course configuration."""
    
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
    
    # Relationships
    user = relationship('User', back_populates='modules')
    schedules = relationship('Schedule', back_populates='module', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Module {self.code} - {self.name}>"
    
    def to_dict(self):
        """Convert to dictionary."""
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
    """Generation schedule."""
    
    __tablename__ = 'schedules'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    module_id = Column(Integer, ForeignKey('modules.id'), nullable=False)
    
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    lab_time = Column(String(10), nullable=False)  # HH:MM format
    generate_before_minutes = Column(Integer, default=60)
    
    current_practical_number = Column(Integer, default=1)
    auto_increment = Column(Boolean, default=True)
    use_zero_padding = Column(Boolean, default=True)
    
    status = Column(String(20), default='active')  # active, paused, disabled
    skip_dates = Column(Text)  # JSON array of ISO dates
    repeat_mode = Column(Boolean, default=False)
    
    upload_to_onedrive = Column(Boolean, default=True)
    send_confirmation = Column(Boolean, default=True)
    
    last_email_sent = Column(DateTime)
    last_generated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='schedules')
    module = relationship('Module', back_populates='schedules')
    
    def __repr__(self):
        return f"<Schedule {self.module.code if self.module else 'N/A'} - Day {self.day_of_week}>"
    
    def get_day_name(self):
        """Get day name."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[self.day_of_week]
    
    def to_dict(self):
        """Convert to dictionary."""
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
    """Track generation history."""
    
    __tablename__ = 'generation_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    module_code = Column(String(50), nullable=False)
    practical_number = Column(Integer, nullable=False)
    filename = Column(String(500), nullable=False)
    
    generated_via = Column(String(50), default='email')  # email, manual, api
    onedrive_link = Column(String(500))
    email_sent = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='generation_history')
    
    def __repr__(self):
        return f"<Generation {self.filename}>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'module_code': self.module_code,
            'practical_number': self.practical_number,
            'filename': self.filename,
            'generated_via': self.generated_via,
            'onedrive_link': self.onedrive_link,
            'created_at': self.created_at.isoformat()
        }


# Database initialization
def init_database(database_url=None):
    """Initialize database."""
    if database_url is None:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///labsheets.db')
    
    # Fix Render's postgres:// to postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    return Session()


def get_db_session():
    """Get database session."""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///labsheets.db')
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()
