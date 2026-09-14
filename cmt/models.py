from datetime import datetime, date
from extensions import db


def today():
    return date.today()


class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="Admin")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, default="")

    conferences = db.relationship("Conference", backref="department", lazy=True)


class Conference(db.Model):
    __tablename__ = "conferences"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    description = db.Column(db.Text, default="")
    objectives = db.Column(db.Text, default="")
    status_override = db.Column(db.String(20), nullable=True)  # past/current/upcoming or None=auto
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(255), default="")
    registration_fee = db.Column(db.Integer, default=0)
    registration_deadline = db.Column(db.Date, nullable=False)
    submission_deadline = db.Column(db.Date, nullable=False)
    brochure = db.Column(db.String(255), nullable=True)
    flyer = db.Column(db.String(255), nullable=True)
    contact_email = db.Column(db.String(120), default="")
    contact_phone = db.Column(db.String(50), default="")
    keynote_speakers = db.Column(db.Text, default="")   # newline separated
    committee = db.Column(db.Text, default="")           # newline separated
    schedule = db.Column(db.Text, default="")             # newline separated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship("Submission", backref="conference", lazy=True)
    registrations = db.relationship("Registration", backref="conference", lazy=True)

    @property
    def status(self):
        if self.status_override:
            return self.status_override
        t = today()
        if t < self.start_date:
            return "upcoming"
        elif self.start_date <= t <= self.end_date:
            return "current"
        else:
            return "past"

    @property
    def days_to_start(self):
        return (self.start_date - today()).days


class Author(db.Model):
    __tablename__ = "authors"
    id = db.Column(db.Integer, primary_key=True)
    author_code = db.Column(db.String(30), unique=True, nullable=False)  # e.g. AUT-0001
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    mobile = db.Column(db.String(30), default="")
    institution = db.Column(db.String(255), default="")
    department = db.Column(db.String(150), default="")
    designation = db.Column(db.String(150), default="")
    country = db.Column(db.String(100), default="")
    city = db.Column(db.String(100), default="")
    address = db.Column(db.Text, default="")
    verification_status = db.Column(db.String(20), default="Pending")  # Pending/Verified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship("Submission", backref="author", lazy=True)
    registrations = db.relationship("Registration", backref="author", lazy=True)


class Submission(db.Model):
    __tablename__ = "submissions"
    id = db.Column(db.Integer, primary_key=True)
    abstract_id = db.Column(db.String(30), unique=True, nullable=False)  # CMT-2026-0001
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=False)
    conference_id = db.Column(db.Integer, db.ForeignKey("conferences.id"), nullable=False)
    paper_title = db.Column(db.String(300), nullable=False)
    abstract = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.String(300), default="")
    co_authors = db.Column(db.String(300), default="")
    presentation_type = db.Column(db.String(30), default="Paper Presentation")
    paper_file = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), default="Submitted")
    reviewer_comments = db.Column(db.Text, default="")
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Registration(db.Model):
    __tablename__ = "registrations"
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.String(30), unique=True, nullable=False)  # REG-00001
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=False)
    conference_id = db.Column(db.Integer, db.ForeignKey("conferences.id"), nullable=False)
    payment_id = db.Column(db.String(30), nullable=True)
    amount = db.Column(db.Integer, default=0)
    payment_status = db.Column(db.String(20), default="Pending")  # Pending/Paid
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, default="")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255), default="")
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
