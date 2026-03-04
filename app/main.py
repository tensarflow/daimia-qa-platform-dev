from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mercedes-benz-quality-assurance-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'mercedes_qa.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer)
    title = db.Column(db.String(200), nullable=False)
    subsections = db.relationship('Subsection', backref='section', lazy=True, cascade="all, delete-orphan")

class Subsection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    order = db.Column(db.Integer)
    title = db.Column(db.String(200), nullable=False)
    questions = db.relationship('Question', backref='subsection', lazy=True, cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subsection_id = db.Column(db.Integer, db.ForeignKey('subsection.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='yes_no') # yes_no, text, rating
    description = db.Column(db.Text) # For detailed guidance from Excel
    order = db.Column(db.Integer)

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_name = db.Column(db.String(200))
    vin_number = db.Column(db.String(100)) # Added VIN field
    model_series = db.Column(db.String(100)) # Added Model Series field
    status = db.Column(db.String(50), default='draft') # draft, completed
    answers = db.relationship('Answer', backref='assessment', lazy=True, cascade="all, delete-orphan")

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    value = db.Column(db.Text)

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    assessments = Assessment.query.filter_by(user_id=session['user_id']).order_by(Assessment.created_at.desc()).all()
    return render_template('dashboard.html', assessments=assessments)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/assessment/new', methods=['GET', 'POST'])
def new_assessment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        project = request.form.get('project_name')
        vin = request.form.get('vin_number')
        series = request.form.get('model_series')
        new_asmt = Assessment(
            user_id=session['user_id'], 
            project_name=project,
            vin_number=vin,
            model_series=series
        )
        db.session.add(new_asmt)
        db.session.commit()
        return redirect(url_for('fill_assessment', id=new_asmt.id))
    return render_template('new_assessment.html')

@app.route('/assessment/<int:id>', methods=['GET', 'POST'])
def fill_assessment(id):
    asmt = Assessment.query.get_or_404(id)
    if asmt.user_id != session['user_id'] and not session.get('is_admin'):
        return redirect(url_for('index'))
    
    sections = Section.query.order_by(Section.order).all()
    
    if request.method == 'POST':
        # Save answers logic
        data = request.form.to_dict()
        for key, value in data.items():
            if key.startswith('q_'):
                q_id = int(key.split('_')[1])
                ans = Answer.query.filter_by(assessment_id=id, question_id=q_id).first()
                if not ans:
                    ans = Answer(assessment_id=id, question_id=q_id)
                    db.session.add(ans)
                ans.value = value
        db.session.commit()
        flash('Progress saved')
        return redirect(url_for('index'))

    # Load existing answers
    existing_answers = {a.question_id: a.value for a in asmt.answers}
    return render_template('assessment_form.html', asmt=asmt, sections=sections, answers=existing_answers)

# Admin Routes
@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return "Access Denied", 403
    sections = Section.query.order_by(Section.order).all()
    return render_template('admin/dashboard.html', sections=sections)

@app.route('/admin/section/add', methods=['POST'])
def add_section():
    title = request.form.get('title')
    order = Section.query.count() + 1
    new_s = Section(title=title, order=order)
    db.session.add(new_s)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/subsection/add/<int:section_id>', methods=['POST'])
def add_subsection(section_id):
    title = request.form.get('title')
    order = Subsection.query.filter_by(section_id=section_id).count() + 1
    new_sub = Subsection(title=title, section_id=section_id, order=order)
    db.session.add(new_sub)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/question/add/<int:subsection_id>', methods=['POST'])
def add_question(subsection_id):
    text = request.form.get('text')
    q_type = request.form.get('type', 'yes_no')
    new_q = Question(text=text, subsection_id=subsection_id, type=q_type)
    db.session.add(new_q)
    db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Seed admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin', 
                password=generate_password_hash('mercedes123'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
    app.run(host='0.0.0.0', port=8091)
