from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os
import secrets

# Flask App Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shramic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Flask-Mail Configuration (Update with your credentials)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'shramicnetworks@gmail.com'
app.config['MAIL_PASSWORD'] = '1211 4545 4545'
app.config['MAIL_DEFAULT_SENDER'] = 'Shramic <shramicnetworks@gmail.com>'

db = SQLAlchemy(app)
mail = Mail(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ======================= DATABASE MODELS =======================

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Internship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    location_type = db.Column(db.String(50), default='remote')  # remote, onsite, hybrid
    deadline = db.Column(db.Date, nullable=False)
    duration = db.Column(db.String(50))
    stipend = db.Column(db.String(100))
    required_fields = db.Column(db.Text)  # JSON string of required fields
    optional_fields = db.Column(db.Text)  # JSON string of optional fields
    image_url = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    applicants = db.relationship('Applicant', backref='internship', lazy=True, cascade='all, delete-orphan')

class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    internship_id = db.Column(db.Integer, db.ForeignKey('internship.id'), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    resume_path = db.Column(db.String(300), nullable=False)
    cover_letter = db.Column(db.Text)
    linkedin_url = db.Column(db.String(300))
    portfolio_url = db.Column(db.String(300))
    additional_info = db.Column(db.Text)  # JSON string of additional form data
    status = db.Column(db.String(50), default='pending')  # pending, reviewed, shortlisted, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), default='Shramic')
    tagline = db.Column(db.String(200), default='Empowering Careers Through Excellence')
    about_text = db.Column(db.Text)
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    social_linkedin = db.Column(db.String(300))
    social_twitter = db.Column(db.String(300))
    social_facebook = db.Column(db.String(300))
    logo_url = db.Column(db.String(300), default='/static/img/logo.png')

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# ======================= HELPER FUNCTIONS =======================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx'}

def create_slug(title):
    return title.lower().replace(' ', '-').replace('/', '-')

def get_site_settings():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)
        db.session.commit()
    return settings

# ======================= PUBLIC ROUTES =======================

@app.route('/')
def index():
    settings = get_site_settings()
    featured_internships = Internship.query.filter_by(is_active=True).order_by(Internship.created_at.desc()).limit(6).all()
    return render_template('index.html', settings=settings, internships=featured_internships)

@app.route('/internships')
def internships():
    settings = get_site_settings()
    page = request.args.get('page', 1, type=int)
    location_filter = request.args.get('location', 'all')

    query = Internship.query.filter_by(is_active=True)

    if location_filter != 'all':
        query = query.filter_by(location_type=location_filter)

    internships_paginated = query.order_by(Internship.created_at.desc()).paginate(page=page, per_page=9, error_out=False)

    return render_template('internships.html', settings=settings, internships=internships_paginated, location_filter=location_filter)

@app.route('/internships/<slug>')
def internship_detail(slug):
    settings = get_site_settings()
    internship = Internship.query.filter_by(slug=slug, is_active=True).first_or_404()
    return render_template('internship_detail.html', settings=settings, internship=internship)

@app.route('/apply/<slug>', methods=['GET', 'POST'])
def apply(slug):
    settings = get_site_settings()
    internship = Internship.query.filter_by(slug=slug, is_active=True).first_or_404()

    if request.method == 'POST':
        try:
            # Validate required fields
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()

            if not all([full_name, email, phone]):
                flash('Please fill all required fields.', 'danger')
                return redirect(url_for('apply', slug=slug))

            # Handle file upload
            if 'resume' not in request.files:
                flash('Resume is required.', 'danger')
                return redirect(url_for('apply', slug=slug))

            file = request.files['resume']
            if file.filename == '':
                flash('Please select a resume file.', 'danger')
                return redirect(url_for('apply', slug=slug))

            if file and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Create applicant record
                applicant = Applicant(
                    internship_id=internship.id,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    resume_path=filename,
                    cover_letter=request.form.get('cover_letter', ''),
                    linkedin_url=request.form.get('linkedin_url', ''),
                    portfolio_url=request.form.get('portfolio_url', '')
                )

                db.session.add(applicant)
                db.session.commit()

                # Send confirmation email to applicant
                try:
                    msg = Message(
                        f'Application Received - {internship.title}',
                        recipients=[email]
                    )
                    msg.html = render_template('emails/application_confirmation.html',
                                              applicant=applicant,
                                              internship=internship,
                                              settings=settings)
                    mail.send(msg)
                except Exception as e:
                    print(f"Email error: {e}")

                flash('Application submitted successfully! We will contact you soon.', 'success')
                return redirect(url_for('internships'))
            else:
                flash('Invalid file format. Please upload PDF, DOC, or DOCX.', 'danger')
                return redirect(url_for('apply', slug=slug))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('apply', slug=slug))

    return render_template('apply.html', settings=settings, internship=internship)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    settings = get_site_settings()

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            subject = request.form.get('subject', '').strip()
            message = request.form.get('message', '').strip()

            if not all([name, email, message]):
                flash('Please fill all required fields.', 'danger')
                return redirect(url_for('contact'))

            contact_msg = ContactMessage(
                name=name,
                email=email,
                subject=subject,
                message=message
            )

            db.session.add(contact_msg)
            db.session.commit()

            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('contact'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('contact'))

    return render_template('contact.html', settings=settings)

@app.route('/admin/search')
@login_required
def admin_search():
    query = request.args.get('q', '').strip().lower()

    if not query:
        return jsonify([])

    results = []

    # Define searchable items with their metadata
    search_items = [
        {
            'title': 'Dashboard',
            'url': url_for('admin_dashboard'),
            'icon': 'home',
            'category': 'Navigation',
            'keywords': ['home', 'overview', 'stats', 'statistics', 'dashboard']
        },
        {
            'title': 'Post Internship',
            'url': url_for('post_intern'),
            'icon': 'plus-circle',
            'category': 'Internships',
            'keywords': ['create', 'add', 'new', 'posting', 'post', 'internship']
        },
        {
            'title': 'Manage Internships',
            'url': url_for('admin_internships'),
            'icon': 'briefcase',
            'category': 'Internships',
            'keywords': ['edit', 'delete', 'view', 'all', 'manage', 'internship', 'internships']
        },
        {
            'title': 'All Applicants',
            'url': url_for('admin_applicants'),
            'icon': 'users',
            'category': 'Applications',
            'keywords': ['candidates', 'applications', 'resumes', 'applicants', 'applicant']
        },
        {
            'title': 'Send Email',
            'url': url_for('admin_mail'),
            'icon': 'envelope',
            'category': 'Communication',
            'keywords': ['mail', 'message', 'contact', 'send', 'email']
        },
        {
            'title': 'Messages',
            'url': url_for('admin_messages'),
            'icon': 'inbox',
            'category': 'Communication',
            'keywords': ['inbox', 'contact', 'queries', 'feedback', 'messages', 'message']
        },
        {
            'title': 'Site Settings',
            'url': url_for('admin_settings'),
            'icon': 'cog',
            'category': 'Settings',
            'keywords': ['configuration', 'preferences', 'setup', 'settings', 'site']
        },
        {
            'title': 'View Site',
            'url': url_for('index'),
            'icon': 'external-link-alt',
            'category': 'Navigation',
            'keywords': ['website', 'public', 'frontend', 'view', 'site']
        },
        {
            'title': 'Logout',
            'url': url_for('admin_logout'),
            'icon': 'sign-out-alt',
            'category': 'Account',
            'keywords': ['signout', 'exit', 'leave', 'logout']
        }
    ]

    # Search through internships
    internships = Internship.query.all()
    for internship in internships:
        search_items.append({
            'title': internship.title,
            'url': url_for('edit_internship', id=internship.id),
            'icon': 'briefcase',
            'category': 'Internship',
            'keywords': [internship.location.lower(), internship.skills.lower(), internship.location_type.lower(), internship.title.lower()],
            'subtitle': f"{internship.location} • {internship.location_type}"
        })

    # Search through applicants
    applicants = Applicant.query.all()
    for applicant in applicants:
        search_items.append({
            'title': applicant.full_name,
            'url': url_for('view_applicant', id=applicant.id),
            'icon': 'user',
            'category': 'Applicant',
            'keywords': [applicant.email.lower(), applicant.phone, applicant.internship.title.lower(), applicant.full_name.lower()],
            'subtitle': f"{applicant.email} • Applied for {applicant.internship.title}"
        })

    # Improved matching - only exact/substring matches
    def matches_query(text, query):
        """Check if query matches text (substring match)"""
        text = text.lower()
        query = query.lower()

        # Direct substring match
        if query in text:
            return True

        # Word boundary match (query matches start of any word)
        words = text.split()
        for word in words:
            if word.startswith(query):
                return True

        return False

    # Search and filter results
    for item in search_items:
        matched = False

        # Check title
        if matches_query(item['title'], query):
            matched = True

        # Check keywords
        if not matched:
            for keyword in item.get('keywords', []):
                if matches_query(keyword, query):
                    matched = True
                    break

        # Check category
        if not matched:
            if matches_query(item['category'], query):
                matched = True

        # Check subtitle if exists
        if not matched and item.get('subtitle'):
            if matches_query(item['subtitle'], query):
                matched = True

        # Add to results if matched
        if matched:
            results.append({
                'title': item['title'],
                'url': item['url'],
                'icon': item['icon'],
                'category': item['category'],
                'subtitle': item.get('subtitle', '')
            })

    # Limit results
    return jsonify(results[:15])
# ======================= ADMIN ROUTES =======================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            flash('Welcome back!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    settings = get_site_settings()
    total_internships = Internship.query.count()
    active_internships = Internship.query.filter_by(is_active=True).count()
    total_applicants = Applicant.query.count()
    pending_applicants = Applicant.query.filter_by(status='pending').count()
    total_messages = ContactMessage.query.count()
    unread_messages = ContactMessage.query.filter_by(is_read=False).count()

    recent_applicants = Applicant.query.order_by(Applicant.applied_at.desc()).limit(5).all()
    recent_internships = Internship.query.order_by(Internship.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                         settings=settings,
                         total_internships=total_internships,
                         active_internships=active_internships,
                         total_applicants=total_applicants,
                         pending_applicants=pending_applicants,
                         total_messages=total_messages,
                         unread_messages=unread_messages,
                         recent_applicants=recent_applicants,
                         recent_internships=recent_internships)

@app.route('/admin/post_intern', methods=['GET', 'POST'])
@login_required
def post_intern():
    settings = get_site_settings()

    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            skills = request.form.get('skills', '').strip()
            location = request.form.get('location', '').strip()
            location_type = request.form.get('location_type', 'remote')
            deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d').date()
            duration = request.form.get('duration', '').strip()
            stipend = request.form.get('stipend', '').strip()

            if not all([title, description, skills, location, deadline]):
                flash('Please fill all required fields.', 'danger')
                return redirect(url_for('post_intern'))

            slug = create_slug(title)

            # Check if slug exists
            existing = Internship.query.filter_by(slug=slug).first()
            if existing:
                slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            internship = Internship(
                title=title,
                slug=slug,
                description=description,
                skills=skills,
                location=location,
                location_type=location_type,
                deadline=deadline,
                duration=duration,
                stipend=stipend,
                is_active=True
            )

            db.session.add(internship)
            db.session.commit()

            flash('Internship posted successfully!', 'success')
            return redirect(url_for('admin_internships'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('post_intern'))

    return render_template('admin/post_intern.html', settings=settings)

@app.route('/admin/internships')
@login_required
def admin_internships():
    settings = get_site_settings()
    page = request.args.get('page', 1, type=int)
    internships = Internship.query.order_by(Internship.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('admin/internships.html', settings=settings, internships=internships)

@app.route('/admin/internships/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_internship(id):
    settings = get_site_settings()
    internship = Internship.query.get_or_404(id)

    if request.method == 'POST':
        try:
            internship.title = request.form.get('title', '').strip()
            internship.description = request.form.get('description', '').strip()
            internship.skills = request.form.get('skills', '').strip()
            internship.location = request.form.get('location', '').strip()
            internship.location_type = request.form.get('location_type', 'remote')
            internship.deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d').date()
            internship.duration = request.form.get('duration', '').strip()
            internship.stipend = request.form.get('stipend', '').strip()
            internship.is_active = request.form.get('is_active') == 'on'
            internship.updated_at = datetime.utcnow()

            db.session.commit()
            flash('Internship updated successfully!', 'success')
            return redirect(url_for('admin_internships'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('admin/edit_internship.html', settings=settings, internship=internship)

@app.route('/admin/internships/<int:id>/delete', methods=['POST'])
@login_required
def delete_internship(id):
    try:
        internship = Internship.query.get_or_404(id)
        db.session.delete(internship)
        db.session.commit()
        flash('Internship deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')

    return redirect(url_for('admin_internships'))

@app.route('/admin/applicants')
@login_required
def admin_applicants():
    settings = get_site_settings()
    page = request.args.get('page', 1, type=int)
    internship_id = request.args.get('internship', type=int)
    status_filter = request.args.get('status', 'all')

    query = Applicant.query

    if internship_id:
        query = query.filter_by(internship_id=internship_id)

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    applicants = query.order_by(Applicant.applied_at.desc()).paginate(page=page, per_page=20, error_out=False)
    internships = Internship.query.all()

    return render_template('admin/applicants.html',
                         settings=settings,
                         applicants=applicants,
                         internships=internships,
                         selected_internship=internship_id,
                         status_filter=status_filter)

@app.route('/admin/applicants/<int:id>')
@login_required
def view_applicant(id):
    settings = get_site_settings()
    applicant = Applicant.query.get_or_404(id)
    return render_template('admin/view_applicant.html', settings=settings, applicant=applicant)

@app.route('/admin/applicants/<int:id>/status', methods=['POST'])
@login_required
def update_applicant_status(id):
    try:
        applicant = Applicant.query.get_or_404(id)
        applicant.status = request.form.get('status', 'pending')
        db.session.commit()
        flash('Status updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')

    return redirect(url_for('view_applicant', id=id))

@app.route('/admin/mail', methods=['GET', 'POST'])
@login_required
def admin_mail():
    settings = get_site_settings()

    if request.method == 'POST':
        try:
            recipient_ids = request.form.getlist('recipients')
            subject = request.form.get('subject', '').strip()
            message_body = request.form.get('message', '').strip()

            if not all([recipient_ids, subject, message_body]):
                flash('Please fill all required fields and select recipients.', 'danger')
                return redirect(url_for('admin_mail'))

            recipients = Applicant.query.filter(Applicant.id.in_(recipient_ids)).all()

            for recipient in recipients:
                msg = Message(subject, recipients=[recipient.email])
                msg.html = render_template('emails/custom_email.html',
                                          recipient=recipient,
                                          message_body=message_body,
                                          settings=settings)
                mail.send(msg)

            flash(f'Email sent successfully to {len(recipients)} recipient(s)!', 'success')
            return redirect(url_for('admin_mail'))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('admin_mail'))

    applicants = Applicant.query.order_by(Applicant.applied_at.desc()).all()
    return render_template('admin/mail.html', settings=settings, applicants=applicants)

@app.route('/admin/messages')
@login_required
def admin_messages():
    settings = get_site_settings()
    page = request.args.get('page', 1, type=int)
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/messages.html', settings=settings, messages=messages)

@app.route('/admin/messages/<int:id>')
@login_required
def view_message(id):
    settings = get_site_settings()
    message = ContactMessage.query.get_or_404(id)
    message.is_read = True
    db.session.commit()
    return render_template('admin/view_message.html', settings=settings, message=message)

@app.route('/admin/messages/<int:id>/delete', methods=['POST'])
@login_required
def delete_message(id):
    try:
        message = ContactMessage.query.get_or_404(id)
        db.session.delete(message)
        db.session.commit()
        flash('Message deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')

    return redirect(url_for('admin_messages'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    settings = get_site_settings()

    if request.method == 'POST':
        try:
            settings.company_name = request.form.get('company_name', '').strip()
            settings.tagline = request.form.get('tagline', '').strip()
            settings.about_text = request.form.get('about_text', '').strip()
            settings.contact_email = request.form.get('contact_email', '').strip()
            settings.contact_phone = request.form.get('contact_phone', '').strip()
            settings.social_linkedin = request.form.get('social_linkedin', '').strip()
            settings.social_twitter = request.form.get('social_twitter', '').strip()
            settings.social_facebook = request.form.get('social_facebook', '').strip()

            db.session.commit()
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('admin_settings'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('admin/settings.html', settings=settings)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ======================= ERROR HANDLERS =======================

@app.errorhandler(404)
def not_found(e):
    settings = get_site_settings()
    return render_template('errors/404.html', settings=settings), 404

@app.errorhandler(500)
def internal_error(e):
    settings = get_site_settings()
    return render_template('errors/500.html', settings=settings), 500

# ======================= INITIALIZATION =======================

def init_db():
    with app.app_context():
        db.create_all()

        # Create default admin if not exists
        if not Admin.query.first():
            admin = Admin(
                username='Shramicadmin',
                password=generate_password_hash('Shramic@2025'),
                email='admin@shramic.com'
            )
            db.session.add(admin)

        # Create default settings if not exists
        if not SiteSettings.query.first():
            settings = SiteSettings(
                company_name='Shramic',
                tagline='Empowering Careers Through Excellence',
                about_text='Shramic is committed to bridging the gap between talented individuals and leading organizations. We provide comprehensive internship opportunities that shape futures and build careers.',
                contact_email='shramicnetworks@gmail.com',
                contact_phone='+91 98765 43210'
            )
            db.session.add(settings)

        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
