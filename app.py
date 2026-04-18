import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, User, JobListing, Application
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobportal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash(f'Access denied. You must be an {role} to view this page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Context Processors ---
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# --- Routes ---

@app.route('/')
def index():
    # Simple search handling
    query = request.args.get('q')
    category = request.args.get('category')
    location = request.args.get('location')
    
    jobs_query = JobListing.query
    if query:
        jobs_query = jobs_query.filter(JobListing.title.ilike(f'%{query}%') | JobListing.company.ilike(f'%{query}%'))
    if category:
        jobs_query = jobs_query.filter(JobListing.category.ilike(f'%{category}%'))
    if location:
        jobs_query = jobs_query.filter(JobListing.location.ilike(f'%{location}%'))
    
    # Simple pagination or limit
    jobs = jobs_query.order_by(JobListing.date_posted.desc()).limit(20).all()
    return render_template('index.html', jobs=jobs, q=query, cat=category, loc=location)

# --- Authenication ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists.', 'warning')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            
            if user.role == 'employer':
                return redirect(url_for('employer_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('seeker_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

# --- Job Seeker Routes ---

@app.route('/dashboard/seeker')
@login_required
@role_required('seeker')
def seeker_dashboard():
    applications = Application.query.filter_by(user_id=current_user.id).all()
    return render_template('seeker/dashboard.html', applications=applications)

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    job = JobListing.query.get_or_404(job_id)
    has_applied = False
    if current_user.is_authenticated and current_user.role == 'seeker':
        application = Application.query.filter_by(job_id=job.id, user_id=current_user.id).first()
        if application:
            has_applied = True
    return render_template('job_detail.html', job=job, has_applied=has_applied)

@app.route('/apply/<int:job_id>', methods=['POST'])
@login_required
@role_required('seeker')
def apply_job(job_id):
    job = JobListing.query.get_or_404(job_id)
    # Check if already applied
    if Application.query.filter_by(job_id=job.id, user_id=current_user.id).first():
        flash("You've already applied for this job.", 'warning')
        return redirect(url_for('job_detail', job_id=job.id))
        
    cover_letter = request.form.get('cover_letter', '')
    resume_link = request.form.get('resume_link', '')
    
    app_record = Application(job_id=job.id, user_id=current_user.id, cover_letter=cover_letter, resume_link=resume_link)
    db.session.add(app_record)
    db.session.commit()
    
    flash('Successfully applied to the job!', 'success')
    return redirect(url_for('seeker_dashboard'))

# --- Employer Routes ---

@app.route('/dashboard/employer')
@login_required
@role_required('employer')
def employer_dashboard():
    jobs = JobListing.query.filter_by(employer_id=current_user.id).all()
    return render_template('employer/dashboard.html', jobs=jobs)

@app.route('/dashboard/employer/post', methods=['GET', 'POST'])
@login_required
@role_required('employer')
def post_job():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        salary = request.form.get('salary')
        location = request.form.get('location')
        category = request.form.get('category')
        company = request.form.get('company')
        
        job = JobListing(title=title, description=description, salary=salary, location=location, 
                         category=category, company=company, employer_id=current_user.id)
        db.session.add(job)
        db.session.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('employer_dashboard'))
    return render_template('employer/post_job.html')

@app.route('/dashboard/employer/job/<int:job_id>/applications')
@login_required
@role_required('employer')
def job_applications(job_id):
    job = JobListing.query.get_or_404(job_id)
    if job.employer_id != current_user.id:
        flash("Access Denied", "danger")
        return redirect(url_for('employer_dashboard'))
    
    applications = Application.query.filter_by(job_id=job.id).all()
    return render_template('employer/applications.html', job=job, applications=applications)

@app.route('/dashboard/employer/application/<int:app_id>/update', methods=['POST'])
@login_required
@role_required('employer')
def update_application(app_id):
    application = Application.query.get_or_404(app_id)
    if application.job.employer_id != current_user.id:
        flash("Access Denied", "danger")
        return redirect(url_for('employer_dashboard'))
        
    status = request.form.get('status')
    if status in ['pending', 'accepted', 'rejected']:
        application.status = status
        db.session.commit()
        flash("Application status updated.", "success")
    return redirect(url_for('job_applications', job_id=application.job_id))

@app.route('/dashboard/employer/job/<int:job_id>/delete', methods=['POST'])
@login_required
@role_required('employer')
def delete_job(job_id):
    job = JobListing.query.get_or_404(job_id)
    if job.employer_id != current_user.id:
        flash("Access Denied", "danger")
        return redirect(url_for('employer_dashboard'))
    
    db.session.delete(job)
    db.session.commit()
    flash("Job deleted.", "success")
    return redirect(url_for('employer_dashboard'))


# --- Admin Routes ---

@app.route('/dashboard/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    users = User.query.all()
    jobs = JobListing.query.all()
    return render_template('admin/dashboard.html', users=users, jobs=jobs)

@app.route('/dashboard/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Cannot delete yourself.", "danger")
        return redirect(url_for('admin_dashboard'))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/dashboard/admin/delete_job/<int:job_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_job(job_id):
    job = JobListing.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash("Job deleted.", "success")
    return redirect(url_for('admin_dashboard'))

# --- API Generation (Bonus) ---
# Fetches data from an external mock API to populate database
@app.route('/api/fetch-jobs')
@login_required
@role_required('admin')
def fetch_jobs_api():
    try:
        # Dummy API request for illustration (JSONPlaceholder can't offer real jobs, using a sample structure)
        # We will mock the fetching process by injecting 3 dummy jobs.
        dummy_jobs = [
            {"title": "Software Engineer", "company": "TechCorp", "location": "Remote", "salary": "$100k - $120k", "category": "IT"},
            {"title": "Data Analyst", "company": "DataWorks", "location": "New York, NY", "salary": "$80k - $95k", "category": "Data"},
            {"title": "Marketing Manager", "company": "AdGrowth", "location": "San Francisco, CA", "salary": "$90k - $110k", "category": "Marketing"}
        ]
        
        # Ensure there is an employer to assign to
        employer = User.query.filter_by(role='employer').first()
        if not employer:
            flash("No employer found to assign fetched jobs.", "warning")
            return redirect(url_for('admin_dashboard'))
            
        for d in dummy_jobs:
            job = JobListing(
                title=d["title"],
                company=d["company"],
                location=d["location"],
                salary=d["salary"],
                category=d["category"],
                description="This is a fetched job description.",
                employer_id=employer.id
            )
            db.session.add(job)
        db.session.commit()
        flash("Jobs fetched and stored successfully!", "success")
    except Exception as e:
        flash(f"Error fetching jobs: {str(e)}", "danger")
        
    return redirect(url_for('admin_dashboard'))


# --- Initialization ---
def init_db():
    with app.app_context():
        db.create_all()
        # Create an admin user if not exists
        if not User.query.filter_by(role='admin').first():
            hashed_pw = generate_password_hash("admin123")
            admin = User(username="admin", email="admin@jobportal.com", password=hashed_pw, role="admin")
            db.session.add(admin)
            db.session.commit()
            print("Default admin created (admin / admin123)")

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', debug=True, port=5000)
