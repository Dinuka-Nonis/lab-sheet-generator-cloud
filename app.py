"""
Lab Sheet Generator Cloud Service V3.0 - Multi-User System
Flask application with database, authentication, and automation
"""

from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import os
import logging
import secrets
import json

# Import our modules
from database import (
    init_database, get_db_session, User, Module, Schedule, GenerationHistory
)
from generator import get_document_generator
from email_manager import get_email_manager
from onedrive_manager import get_onedrive_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# ── CORS: allow desktop app (any origin) to POST to API ──────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/api/<path:path>', methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path=''):
    """Handle preflight CORS requests."""
    from flask import Response
    resp = Response('')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp, 200

# Initialize database
try:
    init_database()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization error: {e}")

# Initialize services
document_generator = get_document_generator()
email_manager = get_email_manager()
onedrive_manager = get_onedrive_manager()

# Store for temporary tokens
tokens = {}  # token -> {schedule_id, user_id, action, created_at, expires_at}

# Initialize scheduler
scheduler = BackgroundScheduler()

# Configuration
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')


# ============================================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================================

def require_api_key(f):
    """Decorator to require API key authentication."""
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        db = get_db_session()
        try:
            user = db.query(User).filter_by(api_key=api_key, is_active=True).first()
            if not user:
                return jsonify({'error': 'Invalid API key'}), 401
            
            # Attach user to request
            request.current_user = user
            
            return f(*args, **kwargs)
        finally:
            db.close()
    
    decorated_function.__name__ = f.__name__
    return decorated_function


def generate_token(user_id, schedule_id, action='generate'):
    """Generate secure token for email actions."""
    token = secrets.token_urlsafe(32)
    tokens[token] = {
        'user_id': user_id,
        'schedule_id': schedule_id,
        'action': action,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
    }
    return token


# ============================================================================
# API ROUTES - USER MANAGEMENT
# ============================================================================

@app.route('/')
def home():
    """API status endpoint."""
    db = get_db_session()
    try:
        user_count = db.query(User).count()
        active_schedules = db.query(Schedule).filter_by(status='active').count()
        
        return jsonify({
            'service': 'Lab Sheet Generator Cloud Service',
            'version': '3.0.0',
            'status': 'running',
            'users': user_count,
            'active_schedules': active_schedules,
            'features': [
                'Multi-user support',
                'Email automation',
                'Document generation',
                'OneDrive integration',
                'Email attachments'
            ]
        })
    finally:
        db.close()


@app.route('/api/register', methods=['POST'])
def register():
    """
    Register new user.
    
    Expected JSON:
    {
        "name": "Student Name",
        "student_id": "IT12345",
        "email": "student@university.lk",
        "password": "password123"
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        required = ['name', 'student_id', 'email', 'password']
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        db = get_db_session()
        try:
            # Check if user already exists
            existing = db.query(User).filter(
                (User.student_id == data['student_id']) | 
                (User.email == data['email'])
            ).first()
            
            if existing:
                return jsonify({'error': 'User already exists'}), 400
            
            # Create new user
            user = User(
                name=data['name'],
                student_id=data['student_id'],
                email=data['email'],
                password_hash=User.hash_password(data['password']),
                api_key=User.generate_api_key()
            )
            
            db.add(user)
            db.commit()
            
            logger.info(f"New user registered: {user.student_id}")
            
            return jsonify({
                'success': True,
                'message': 'User registered successfully',
                'user_id': user.id,
                'student_id': user.student_id,
                'api_key': user.api_key
            }), 201
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """
    User login.
    
    Expected JSON:
    {
        "student_id": "IT12345",
        "password": "password123"
    }
    """
    try:
        data = request.json
        
        if 'student_id' not in data or 'password' not in data:
            return jsonify({'error': 'Missing credentials'}), 400
        
        db = get_db_session()
        try:
            user = db.query(User).filter_by(
                student_id=data['student_id'],
                is_active=True
            ).first()
            
            if not user or not user.verify_password(data['password']):
                return jsonify({'error': 'Invalid credentials'}), 401
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            
            logger.info(f"User logged in: {user.student_id}")
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict(),
                'api_key': user.api_key
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/profile', methods=['GET'])
@require_api_key
def get_profile():
    """Get current user profile."""
    return jsonify({
        'success': True,
        'user': request.current_user.to_dict()
    })


# ============================================================================
# API ROUTES - MODULE MANAGEMENT
# ============================================================================

@app.route('/api/modules', methods=['GET', 'POST'])
@require_api_key
def manage_modules():
    """Get all modules or create new module."""
    
    if request.method == 'GET':
        # Get user's modules
        modules = [m.to_dict() for m in request.current_user.modules]
        return jsonify({
            'success': True,
            'modules': modules
        })
    
    elif request.method == 'POST':
        # Create new module
        try:
            data = request.json
            
            db = get_db_session()
            try:
                module = Module(
                    user_id=request.current_user.id,
                    code=data['code'],
                    name=data['name'],
                    template=data.get('template', 'classic'),
                    sheet_type=data.get('sheet_type', 'Practical'),
                    custom_sheet_type=data.get('custom_sheet_type'),
                    use_zero_padding=data.get('use_zero_padding', True),
                    output_path=data.get('output_path')
                )
                
                db.add(module)
                db.commit()
                
                logger.info(f"Module created: {module.code} for user {request.current_user.student_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Module created',
                    'module': module.to_dict()
                }), 201
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Module creation error: {e}")
            return jsonify({'error': str(e)}), 500


@app.route('/api/modules/<int:module_id>', methods=['PUT', 'DELETE'])
@require_api_key
def update_delete_module(module_id):
    """Update or delete module."""
    
    db = get_db_session()
    try:
        module = db.query(Module).filter_by(
            id=module_id,
            user_id=request.current_user.id
        ).first()
        
        if not module:
            return jsonify({'error': 'Module not found'}), 404
        
        if request.method == 'PUT':
            # Update module
            data = request.json
            
            for key in ['code', 'name', 'template', 'sheet_type', 'custom_sheet_type', 
                       'use_zero_padding', 'output_path']:
                if key in data:
                    setattr(module, key, data[key])
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Module updated',
                'module': module.to_dict()
            })
        
        elif request.method == 'DELETE':
            # Delete module
            db.delete(module)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Module deleted'
            })
            
    finally:
        db.close()


# TO BE CONTINUED IN PART 2...
"""
Lab Sheet Generator Cloud Service - Part 2
Schedule management and document generation endpoints
"""

# CONTINUATION FROM PART 1...

# ============================================================================
# API ROUTES - SCHEDULE MANAGEMENT  
# ============================================================================

@app.route('/api/schedules', methods=['GET', 'POST'])
@require_api_key
def manage_schedules():
    """Get all schedules or create new schedule."""
    
    if request.method == 'GET':
        # Get user's schedules
        schedules = [s.to_dict() for s in request.current_user.schedules]
        return jsonify({
            'success': True,
            'schedules': schedules
        })
    
    elif request.method == 'POST':
        # Create new schedule
        try:
            data = request.json
            
            db = get_db_session()
            try:
                # Verify module belongs to user
                module = db.query(Module).filter_by(
                    id=data['module_id'],
                    user_id=request.current_user.id
                ).first()
                
                if not module:
                    return jsonify({'error': 'Module not found'}), 404
                
                schedule = Schedule(
                    user_id=request.current_user.id,
                    module_id=data['module_id'],
                    day_of_week=data['day_of_week'],
                    lab_time=data['lab_time'],
                    generate_before_minutes=data.get('generate_before_minutes', 60),
                    current_practical_number=data.get('current_practical_number', 1),
                    auto_increment=data.get('auto_increment', True),
                    use_zero_padding=data.get('use_zero_padding', True),
                    status='active',
                    skip_dates=json.dumps([]),
                    repeat_mode=False,
                    upload_to_onedrive=data.get('upload_to_onedrive', True),
                    send_confirmation=data.get('send_confirmation', True)
                )
                
                db.add(schedule)
                db.commit()
                
                logger.info(f"Schedule created for user {request.current_user.student_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Schedule created',
                    'schedule': schedule.to_dict()
                }), 201
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Schedule creation error: {e}")
            return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/<int:schedule_id>', methods=['PUT', 'DELETE'])
@require_api_key
def update_delete_schedule(schedule_id):
    """Update or delete schedule."""
    
    db = get_db_session()
    try:
        schedule = db.query(Schedule).filter_by(
            id=schedule_id,
            user_id=request.current_user.id
        ).first()
        
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        if request.method == 'PUT':
            # Update schedule
            data = request.json
            
            for key in ['day_of_week', 'lab_time', 'generate_before_minutes',
                       'current_practical_number', 'auto_increment', 'use_zero_padding',
                       'status', 'upload_to_onedrive', 'send_confirmation']:
                if key in data:
                    setattr(schedule, key, data[key])
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Schedule updated',
                'schedule': schedule.to_dict()
            })
        
        elif request.method == 'DELETE':
            # Delete schedule
            db.delete(schedule)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Schedule deleted'
            })
            
    finally:
        db.close()


@app.route('/api/schedules/sync', methods=['POST'])
@require_api_key
def sync_schedules():
    """
    Bulk sync schedules from desktop app.
    
    Expected JSON:
    {
        "modules": [...],
        "schedules": [...]
    }
    """
    try:
        data = request.json
        
        db = get_db_session()
        try:
            # Clear existing modules and schedules
            db.query(Module).filter_by(user_id=request.current_user.id).delete()
            db.commit()
            
            # Add modules
            module_map = {}  # old_id -> new module
            for mod_data in data.get('modules', []):
                module = Module(
                    user_id=request.current_user.id,
                    **{k: v for k, v in mod_data.items() if k != 'id'}
                )
                db.add(module)
                db.flush()
                module_map[mod_data.get('id')] = module
            
            # Add schedules
            for sched_data in data.get('schedules', []):
                old_module_id = sched_data.get('module_id')
                if old_module_id in module_map:
                    schedule = Schedule(
                        user_id=request.current_user.id,
                        module_id=module_map[old_module_id].id,
                        **{k: v for k, v in sched_data.items() 
                           if k not in ['id', 'module_id', 'user_id']}
                    )
                    db.add(schedule)
            
            db.commit()
            
            logger.info(f"Synced data for user {request.current_user.student_id}")
            
            return jsonify({
                'success': True,
                'message': 'Data synced successfully',
                'modules': len(data.get('modules', [])),
                'schedules': len(data.get('schedules', []))
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# EMAIL ACTION ENDPOINTS
# ============================================================================

@app.route('/api/generate/<token>', methods=['GET'])
def generate_from_email(token):
    """Generate lab sheet from email button click."""
    
    try:
        # Validate token
        if token not in tokens:
            return render_template_string(ERROR_PAGE, 
                                        message="Invalid or expired link"), 400
        
        token_data = tokens[token]
        
        # Check expiry
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            del tokens[token]
            return render_template_string(ERROR_PAGE, 
                                        message="Link has expired"), 400
        
        user_id = token_data['user_id']
        schedule_id = token_data['schedule_id']
        
        db = get_db_session()
        try:
            # Get user and schedule
            user = db.query(User).get(user_id)
            schedule = db.query(Schedule).get(schedule_id)
            
            if not user or not schedule:
                return render_template_string(ERROR_PAGE,
                                            message="User or schedule not found"), 404
            
            module = schedule.module
            
            logger.info(f"Generating sheet for {user.student_id} - {module.code}")
            
            # Generate document
            doc_path = document_generator.generate(user, module, schedule)
            
            # Upload to OneDrive if enabled
            onedrive_link = None
            if schedule.upload_to_onedrive and onedrive_manager.enabled:
                result = onedrive_manager.upload_file(doc_path, user.student_id)
                if result['success']:
                    onedrive_link = result['share_link']
                    logger.info(f"Uploaded to OneDrive: {onedrive_link}")
            
            # Send confirmation email with attachment
            if schedule.send_confirmation and email_manager.enabled:
                email_manager.send_confirmation_email(
                    to_email=user.email,
                    student_name=user.name,
                    module_name=module.name,
                    practical_number=schedule.current_practical_number,
                    sheet_type=module.sheet_type,
                    onedrive_link=onedrive_link,
                    attachment_path=doc_path
                )
            
            # Save to history
            history = GenerationHistory(
                user_id=user.id,
                module_code=module.code,
                practical_number=schedule.current_practical_number,
                filename=os.path.basename(doc_path),
                generated_via='email',
                onedrive_link=onedrive_link,
                email_sent=schedule.send_confirmation
            )
            db.add(history)
            
            # Auto-increment if enabled
            if schedule.auto_increment:
                schedule.current_practical_number += 1
            
            # Update last generated
            schedule.last_generated_at = datetime.utcnow()
            
            db.commit()
            
            # Remove used token
            del tokens[token]
            
            # Clean up file
            try:
                os.remove(doc_path)
            except:
                pass
            
            return render_template_string(SUCCESS_PAGE, 
                                        module=module.name,
                                        practical=schedule.current_practical_number - 1)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return render_template_string(ERROR_PAGE, 
                                    message=f"Error: {str(e)}"), 500


@app.route('/api/skip/<token>', methods=['GET'])
def skip_from_email(token):
    """Skip this week from email button click."""
    
    try:
        # Validate token
        if token not in tokens:
            return render_template_string(ERROR_PAGE,
                                        message="Invalid or expired link"), 400
        
        token_data = tokens[token]
        
        # Check expiry
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            del tokens[token]
            return render_template_string(ERROR_PAGE,
                                        message="Link has expired"), 400
        
        user_id = token_data['user_id']
        schedule_id = token_data['schedule_id']
        
        db = get_db_session()
        try:
            schedule = db.query(Schedule).get(schedule_id)
            
            if not schedule:
                return render_template_string(ERROR_PAGE,
                                            message="Schedule not found"), 404
            
            # Add today to skip dates
            today = datetime.now().date().isoformat()
            skip_dates = json.loads(schedule.skip_dates or '[]')
            
            if today not in skip_dates:
                skip_dates.append(today)
                schedule.skip_dates = json.dumps(skip_dates)
                db.commit()
            
            logger.info(f"Week skipped for schedule {schedule_id}")
            
            # Remove used token
            del tokens[token]
            
            return render_template_string(SKIP_PAGE,
                                        module=schedule.module.name,
                                        practical=schedule.current_practical_number)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Skip error: {e}")
        return render_template_string(ERROR_PAGE,
                                    message=f"Error: {str(e)}"), 500


# TO BE CONTINUED IN PART 3...
"""
Lab Sheet Generator Cloud Service - Part 3
Scheduler and HTML templates
"""

# CONTINUATION FROM PART 2...

import os

# ============================================================================
# SCHEDULER LOGIC
# ============================================================================

def calculate_next_generation_time(schedule):
    """Calculate when to send generation email."""
    now = datetime.now()
    current_day = now.weekday()
    target_day = schedule.day_of_week
    
    # Parse lab time
    lab_time_parts = schedule.lab_time.split(':')
    lab_hour = int(lab_time_parts[0])
    lab_minute = int(lab_time_parts[1])
    
    # Calculate days until next lab
    days_until_lab = (target_day - current_day) % 7
    
    if days_until_lab == 0:
        lab_datetime = now.replace(hour=lab_hour, minute=lab_minute, second=0, microsecond=0)
        if now >= lab_datetime:
            days_until_lab = 7
    
    next_lab = now + timedelta(days=days_until_lab)
    next_lab = next_lab.replace(hour=lab_hour, minute=lab_minute, second=0, microsecond=0)
    
    # Subtract generation time
    next_generation = next_lab - timedelta(minutes=schedule.generate_before_minutes)
    
    return next_generation


def check_and_send_emails():
    """Check all schedules and send emails for upcoming labs."""
    logger.info("Checking schedules for email notifications...")
    
    db = get_db_session()
    try:
        # Get all active schedules
        schedules = db.query(Schedule).filter_by(status='active').all()
        
        now = datetime.now()
        emails_sent = 0
        
        for schedule in schedules:
            try:
                # Calculate next generation time
                next_gen = calculate_next_generation_time(schedule)
                
                # Check if within 5-minute window
                time_diff = (next_gen - now).total_seconds()
                
                if 0 <= time_diff <= 300:  # 0-5 minutes
                    # Check if email already sent recently
                    if schedule.last_email_sent:
                        last_sent = schedule.last_email_sent
                        if (now - last_sent).total_seconds() < 3600:  # 1 hour
                            continue
                    
                    # Check skip dates
                    skip_dates = json.loads(schedule.skip_dates or '[]')
                    today = now.date().isoformat()
                    if today in skip_dates:
                        logger.info(f"Skipping schedule {schedule.id} - date in skip list")
                        continue
                    
                    # Send email
                    user = schedule.user
                    module = schedule.module
                    
                    # Generate tokens
                    gen_token = generate_token(user.id, schedule.id, 'generate')
                    skip_token = generate_token(user.id, schedule.id, 'skip')
                    
                    # Send notification email
                    if email_manager.enabled:
                        success = email_manager.send_generation_email(
                            to_email=user.email,
                            student_name=user.name,
                            module_name=module.name,
                            module_code=module.code,
                            practical_number=schedule.current_practical_number,
                            day_name=schedule.get_day_name(),
                            lab_time=schedule.lab_time,
                            sheet_type=module.sheet_type,
                            generate_token=gen_token,
                            skip_token=skip_token,
                            base_url=BASE_URL
                        )
                        
                        if success:
                            schedule.last_email_sent = now
                            db.commit()
                            emails_sent += 1
                            logger.info(f"Email sent to {user.email} for {module.code}")
                    
            except Exception as e:
                logger.error(f"Error processing schedule {schedule.id}: {e}")
                continue
        
        if emails_sent > 0:
            logger.info(f"Sent {emails_sent} notification email(s)")
        
    finally:
        db.close()


# ============================================================================
# HTML TEMPLATES FOR SUCCESS/ERROR PAGES
# ============================================================================

SUCCESS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sheet Generated!</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }
        h1 { color: #28a745; margin: 0 0 20px 0; font-size: 32px; }
        p { color: #586069; line-height: 1.6; font-size: 16px; }
        .icon { font-size: 64px; margin-bottom: 20px; }
        .detail { background: #f6f8fa; padding: 15px; border-radius: 8px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">✅</div>
        <h1>Sheet Generated!</h1>
        <p>Your lab sheet has been generated successfully!</p>
        <div class="detail">
            <strong>{{ module }}</strong><br>
            Practical #{{ practical }}
        </div>
        <p><strong>Check your email for:</strong></p>
        <p>📎 File attachment<br>☁️ OneDrive link</p>
        <p style="font-size: 14px; color: #6a737d; margin-top: 30px;">
            You can close this page now.
        </p>
    </div>
</body>
</html>
"""

SKIP_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Week Skipped</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }
        h1 { color: #ffa500; margin: 0 0 20px 0; font-size: 32px; }
        p { color: #586069; line-height: 1.6; font-size: 16px; }
        .icon { font-size: 64px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">⏭️</div>
        <h1>Week Skipped</h1>
        <p>This week's generation has been skipped.</p>
        <p>Next week will still be <strong>Practical #{{ practical }}</strong>.</p>
        <p style="font-size: 14px; color: #6a737d; margin-top: 30px;">
            You can close this page now.
        </p>
    </div>
</body>
</html>
"""

ERROR_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }
        h1 { color: #d73a49; margin: 0 0 20px 0; font-size: 32px; }
        p { color: #586069; line-height: 1.6; font-size: 16px; }
        .icon { font-size: 64px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">❌</div>
        <h1>Error</h1>
        <p>{{ message }}</p>
        <p style="font-size: 14px; color: #6a737d; margin-top: 30px;">
            Please contact support if the problem persists.
        </p>
    </div>
</body>
</html>
"""


# ============================================================================
# SCHEDULER STARTUP — runs under both direct execution AND WSGI (PythonAnywhere)
# ============================================================================

def start_scheduler():
    """Start the background scheduler if not already running."""
    if not scheduler.running:
        scheduler.add_job(
            check_and_send_emails,
            'interval',
            minutes=15,
            id='email_checker'
        )
        scheduler.start()
        logger.info("=" * 60)
        logger.info("Lab Sheet Generator Cloud Service V3.0")
        logger.info("=" * 60)
        logger.info(f"Email enabled: {email_manager.enabled}")
        logger.info(f"OneDrive enabled: {onedrive_manager.enabled}")
        logger.info("Scheduler: running every 15 minutes")
        logger.info(f"Base URL: {BASE_URL}")
        logger.info("=" * 60)


# Start scheduler when module is loaded (works with WSGI)
start_scheduler()


if __name__ == '__main__':
    # Direct execution (local development)
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
