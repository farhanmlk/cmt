import os
import csv
import io
from datetime import datetime, date
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                    session, flash, send_from_directory, Response, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from extensions import db
from models import (Admin, Department, Conference, Author, Submission,
                     Registration, Notification, ContactMessage)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "cmt.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

db.init_app(app)

ALLOWED_DOC_EXT = {"pdf", "doc", "docx"}


def allowed_file(filename, exts):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in exts


# ---------------------------------------------------------------------------
# Helpers / decorators
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("author_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in as admin to continue.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


def current_author():
    aid = session.get("author_id")
    if aid:
        return Author.query.get(aid)
    return None


def current_admin():
    aid = session.get("admin_id")
    if aid:
        return Admin.query.get(aid)
    return None


@app.context_processor
def inject_globals():
    return {
        "current_author": current_author(),
        "current_admin": current_admin(),
        "departments_nav": Department.query.order_by(Department.name).all(),
    }


def gen_author_code():
    n = Author.query.count() + 1
    return f"AUT-{n:04d}"


def gen_abstract_id():
    year = datetime.now().year
    n = Submission.query.count() + 1
    return f"CMT-{year}-{n:04d}"


def gen_registration_id():
    n = Registration.query.count() + 1
    return f"REG-{n:05d}"


def gen_payment_id():
    n = Registration.query.filter(Registration.payment_id.isnot(None)).count() + 1
    return f"PAY-{n:06d}"


def add_notification(author_id, title, message):
    db.session.add(Notification(author_id=author_id, title=title, message=message))


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    all_conf = Conference.query.all()
    current_list = [c for c in all_conf if c.status == "current"]
    upcoming_list = sorted([c for c in all_conf if c.status == "upcoming"], key=lambda c: c.start_date)[:6]
    past_count = len([c for c in all_conf if c.status == "past"])
    stats = {
        "total_conferences": len(all_conf),
        "upcoming": len([c for c in all_conf if c.status == "upcoming"]),
        "authors": Author.query.count(),
        "submissions": Submission.query.count(),
        "accepted": Submission.query.filter(Submission.status.in_(["Accepted", "Final Accepted"])).count(),
    }
    departments = Department.query.all()
    return render_template("index.html", current_list=current_list, upcoming_list=upcoming_list,
                            stats=stats, departments=departments, past_count=past_count)


@app.route("/conferences")
def conferences():
    q = request.args.get("q", "").strip()
    dept_id = request.args.get("department", type=int)
    status = request.args.get("status", "")

    query = Conference.query
    if q:
        query = query.filter(Conference.name.ilike(f"%{q}%"))
    if dept_id:
        query = query.filter(Conference.department_id == dept_id)

    results = query.order_by(Conference.start_date.desc()).all()
    if status:
        results = [c for c in results if c.status == status]

    departments = Department.query.order_by(Department.name).all()
    return render_template("conferences.html", conferences=results, departments=departments,
                            q=q, dept_id=dept_id, status=status)


@app.route("/conference/<int:cid>")
def conference_detail(cid):
    conf = Conference.query.get_or_404(cid)
    return render_template("conference_detail.html", conf=conf)


@app.route("/departments")
def departments():
    depts = Department.query.order_by(Department.name).all()
    counts = {d.id: Conference.query.filter_by(department_id=d.id).count() for d in depts}
    return render_template("departments.html", departments=depts, counts=counts)


@app.route("/department/<int:did>")
def department_detail(did):
    dept = Department.query.get_or_404(did)
    confs = Conference.query.filter_by(department_id=did).order_by(Conference.start_date.desc()).all()
    return render_template("department_detail.html", dept=dept, conferences=confs)


@app.route("/call-for-papers")
def call_for_papers():
    confs = [c for c in Conference.query.all() if c.status in ("upcoming", "current")]
    confs.sort(key=lambda c: c.submission_deadline)
    return render_template("call_for_papers.html", conferences=confs)


@app.route("/materials")
def materials():
    confs = Conference.query.filter(db.or_(Conference.brochure.isnot(None), Conference.flyer.isnot(None))).all()
    return render_template("materials.html", conferences=confs)


@app.route("/download/<kind>/<int:cid>")
def download_material(kind, cid):
    conf = Conference.query.get_or_404(cid)
    fname = conf.brochure if kind == "brochure" else conf.flyer if kind == "flyer" else None
    if not fname:
        abort(404)
    folder = "brochures" if kind == "brochure" else "flyers"
    return send_from_directory(os.path.join(UPLOAD_DIR, folder), fname, as_attachment=True)


@app.route("/download/paper/<int:sid>")
def download_paper(sid):
    sub = Submission.query.get_or_404(sid)
    if not sub.paper_file:
        abort(404)
    return send_from_directory(os.path.join(UPLOAD_DIR, "papers"), sub.paper_file, as_attachment=True)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        msg = ContactMessage(
            name=request.form["name"], email=request.form["email"],
            subject=request.form.get("subject", ""), message=request.form["message"])
        db.session.add(msg)
        db.session.commit()
        flash("Thank you! Your message has been sent to the IEEE Student Branch.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


# ---------------------------------------------------------------------------
# Author auth
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    departments = Department.query.order_by(Department.name).all()
    conferences = Conference.query.order_by(Conference.start_date.desc()).all()
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if Author.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please log in.", "danger")
            return redirect(url_for("register"))

        author = Author(
            author_code=gen_author_code(),
            name=request.form["name"],
            email=email,
            password_hash=generate_password_hash(request.form["password"]),
            mobile=request.form.get("mobile", ""),
            institution=request.form.get("institution", ""),
            department=request.form.get("department", ""),
            designation=request.form.get("designation", ""),
            country=request.form.get("country", ""),
            city=request.form.get("city", ""),
            address=request.form.get("address", ""),
        )
        db.session.add(author)
        db.session.flush()
        add_notification(author.id, "Welcome to CMT",
                          f"Your Author ID is {author.author_code}. You can now submit papers and register for conferences.")
        db.session.commit()
        session["author_id"] = author.id
        flash(f"Registration successful! Your Author ID is {author.author_code}.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html", departments=departments, conferences=conferences)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        author = Author.query.filter_by(email=email).first()
        if author and check_password_hash(author.password_hash, request.form["password"]):
            session["author_id"] = author.id
            flash(f"Welcome back, {author.name}!", "success")
            nxt = request.args.get("next") or url_for("dashboard")
            return redirect(nxt)
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("author_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Author dashboard / submission / registration / payment
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    author = current_author()
    subs = Submission.query.filter_by(author_id=author.id).order_by(Submission.submitted_at.desc()).all()
    regs = Registration.query.filter_by(author_id=author.id).order_by(Registration.registered_at.desc()).all()
    notes = Notification.query.filter_by(author_id=author.id).order_by(Notification.created_at.desc()).limit(10).all()
    accepted = len([s for s in subs if s.status in ("Accepted", "Final Accepted")])
    pending = len([s for s in subs if s.status in ("Submitted", "Under Review", "Revision Required")])
    return render_template("dashboard.html", author=author, submissions=subs, registrations=regs,
                            notifications=notes, accepted=accepted, pending=pending)


@app.route("/submit-paper", methods=["GET", "POST"])
@login_required
def submit_paper():
    author = current_author()
    conferences = Conference.query.order_by(Conference.start_date.desc()).all()
    if request.method == "POST":
        conf_id = int(request.form["conference_id"])
        conf = Conference.query.get_or_404(conf_id)

        filename = None
        file = request.files.get("paper_file")
        if file and file.filename:
            if not allowed_file(file.filename, ALLOWED_DOC_EXT):
                flash("Only PDF/DOC/DOCX files are allowed for the paper.", "danger")
                return redirect(url_for("submit_paper"))
            filename = secure_filename(f"{author.author_code}_{int(datetime.now().timestamp())}_{file.filename}")
            file.save(os.path.join(UPLOAD_DIR, "papers", filename))

        sub = Submission(
            abstract_id=gen_abstract_id(),
            author_id=author.id,
            conference_id=conf.id,
            paper_title=request.form["paper_title"],
            abstract=request.form["abstract"],
            keywords=request.form.get("keywords", ""),
            co_authors=request.form.get("co_authors", ""),
            presentation_type=request.form.get("presentation_type", "Paper Presentation"),
            paper_file=filename,
        )
        db.session.add(sub)
        db.session.flush()
        add_notification(author.id, "Paper submitted successfully",
                          f"Your paper '{sub.paper_title}' was submitted with Abstract ID {sub.abstract_id}.")
        db.session.commit()
        flash("Paper submitted successfully!", "success")
        return redirect(url_for("submission_success", abstract_id=sub.abstract_id))
    return render_template("submit_paper.html", conferences=conferences, author=author)


@app.route("/submission-success/<abstract_id>")
@login_required
def submission_success(abstract_id):
    sub = Submission.query.filter_by(abstract_id=abstract_id).first_or_404()
    return render_template("submission_success.html", sub=sub)


@app.route("/track-submission", methods=["GET", "POST"])
def track_submission():
    sub = None
    searched = False
    if request.method == "POST":
        searched = True
        abstract_id = request.form["abstract_id"].strip()
        email = request.form["email"].strip().lower()
        sub = Submission.query.filter_by(abstract_id=abstract_id).first()
        if not sub or sub.author.email.lower() != email:
            sub = None
            flash("No submission found for that Abstract ID and email combination.", "danger")
    return render_template("track_submission.html", sub=sub, searched=searched)


@app.route("/register-conference/<int:cid>", methods=["GET", "POST"])
@login_required
def register_conference(cid):
    conf = Conference.query.get_or_404(cid)
    author = current_author()
    existing = Registration.query.filter_by(author_id=author.id, conference_id=cid).first()
    if existing:
        return redirect(url_for("payment_page", rid=existing.registration_id))

    reg = Registration(registration_id=gen_registration_id(), author_id=author.id,
                        conference_id=cid, amount=conf.registration_fee, payment_status="Pending")
    db.session.add(reg)
    db.session.commit()
    return redirect(url_for("payment_page", rid=reg.registration_id))


@app.route("/payment/<rid>", methods=["GET", "POST"])
@login_required
def payment_page(rid):
    reg = Registration.query.filter_by(registration_id=rid).first_or_404()
    if reg.author_id != current_author().id:
        abort(403)
    if request.method == "POST":
        reg.payment_id = gen_payment_id()
        reg.payment_status = "Paid"
        db.session.commit()
        add_notification(reg.author_id, "Payment successful",
                          f"Registration payment of Rs.{reg.amount} for {reg.conference.name} completed. Payment ID {reg.payment_id}.")
        db.session.commit()
        flash("Payment successful!", "success")
        return redirect(url_for("payment_receipt", rid=reg.registration_id))
    return render_template("payment.html", reg=reg)


@app.route("/payment-receipt/<rid>")
@login_required
def payment_receipt(rid):
    reg = Registration.query.filter_by(registration_id=rid).first_or_404()
    return render_template("payment_receipt.html", reg=reg)


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password_hash, request.form["password"]):
            session["admin_id"] = admin.id
            flash(f"Welcome, {admin.name}.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "danger")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("admin_login"))


# ---------------------------------------------------------------------------
# Admin dashboard / management
# ---------------------------------------------------------------------------

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    all_conf = Conference.query.all()
    stats = {
        "total": len(all_conf),
        "past": len([c for c in all_conf if c.status == "past"]),
        "current": len([c for c in all_conf if c.status == "current"]),
        "upcoming": len([c for c in all_conf if c.status == "upcoming"]),
        "authors": Author.query.count(),
        "submissions": Submission.query.count(),
        "accepted": Submission.query.filter(Submission.status.in_(["Accepted", "Final Accepted"])).count(),
        "pending_review": Submission.query.filter(Submission.status.in_(["Submitted", "Under Review"])).count(),
        "revenue": db.session.query(db.func.coalesce(db.func.sum(Registration.amount), 0)).filter_by(payment_status="Paid").scalar(),
    }

    dept_counts = {}
    for d in Department.query.all():
        dept_counts[d.name] = Submission.query.join(Conference).filter(Conference.department_id == d.id).count()

    status_counts = {}
    for s in Submission.query.all():
        status_counts[s.status] = status_counts.get(s.status, 0) + 1

    ptype_counts = {}
    for s in Submission.query.all():
        ptype_counts[s.presentation_type] = ptype_counts.get(s.presentation_type, 0) + 1

    monthly = {}
    for s in Submission.query.all():
        key = s.submitted_at.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + 1
    monthly = dict(sorted(monthly.items()))

    return render_template("admin/dashboard.html", stats=stats, dept_counts=dept_counts,
                            status_counts=status_counts, ptype_counts=ptype_counts, monthly=monthly)


@app.route("/admin/conferences")
@admin_required
def admin_conferences():
    confs = Conference.query.order_by(Conference.start_date.desc()).all()
    return render_template("admin/conferences.html", conferences=confs)


@app.route("/admin/conferences/add", methods=["GET", "POST"])
@admin_required
def admin_conference_add():
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        conf = Conference(
            name=request.form["name"],
            department_id=int(request.form["department_id"]),
            description=request.form.get("description", ""),
            objectives=request.form.get("objectives", ""),
            status_override=request.form.get("status_override") or None,
            start_date=datetime.strptime(request.form["start_date"], "%Y-%m-%d").date(),
            end_date=datetime.strptime(request.form["end_date"], "%Y-%m-%d").date(),
            venue=request.form.get("venue", ""),
            registration_fee=int(request.form.get("registration_fee") or 0),
            registration_deadline=datetime.strptime(request.form["registration_deadline"], "%Y-%m-%d").date(),
            submission_deadline=datetime.strptime(request.form["submission_deadline"], "%Y-%m-%d").date(),
            contact_email=request.form.get("contact_email", ""),
            contact_phone=request.form.get("contact_phone", ""),
            keynote_speakers=request.form.get("keynote_speakers", ""),
            committee=request.form.get("committee", ""),
            schedule=request.form.get("schedule", ""),
        )
        _handle_material_uploads(conf, request.files)
        db.session.add(conf)
        db.session.commit()
        flash("Conference created successfully.", "success")
        return redirect(url_for("admin_conferences"))
    return render_template("admin/conference_form.html", departments=departments, conf=None)


@app.route("/admin/conferences/edit/<int:cid>", methods=["GET", "POST"])
@admin_required
def admin_conference_edit(cid):
    conf = Conference.query.get_or_404(cid)
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        conf.name = request.form["name"]
        conf.department_id = int(request.form["department_id"])
        conf.description = request.form.get("description", "")
        conf.objectives = request.form.get("objectives", "")
        conf.status_override = request.form.get("status_override") or None
        conf.start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
        conf.end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()
        conf.venue = request.form.get("venue", "")
        conf.registration_fee = int(request.form.get("registration_fee") or 0)
        conf.registration_deadline = datetime.strptime(request.form["registration_deadline"], "%Y-%m-%d").date()
        conf.submission_deadline = datetime.strptime(request.form["submission_deadline"], "%Y-%m-%d").date()
        conf.contact_email = request.form.get("contact_email", "")
        conf.contact_phone = request.form.get("contact_phone", "")
        conf.keynote_speakers = request.form.get("keynote_speakers", "")
        conf.committee = request.form.get("committee", "")
        conf.schedule = request.form.get("schedule", "")
        _handle_material_uploads(conf, request.files)
        db.session.commit()
        flash("Conference updated successfully.", "success")
        return redirect(url_for("admin_conferences"))
    return render_template("admin/conference_form.html", departments=departments, conf=conf)


def _handle_material_uploads(conf, files):
    brochure = files.get("brochure")
    if brochure and brochure.filename:
        fname = secure_filename(f"{conf.name[:20]}_{int(datetime.now().timestamp())}_{brochure.filename}")
        brochure.save(os.path.join(UPLOAD_DIR, "brochures", fname))
        conf.brochure = fname
    flyer = files.get("flyer")
    if flyer and flyer.filename:
        fname = secure_filename(f"{conf.name[:20]}_{int(datetime.now().timestamp())}_{flyer.filename}")
        flyer.save(os.path.join(UPLOAD_DIR, "flyers", fname))
        conf.flyer = fname


@app.route("/admin/conferences/delete/<int:cid>", methods=["POST"])
@admin_required
def admin_conference_delete(cid):
    conf = Conference.query.get_or_404(cid)
    db.session.delete(conf)
    db.session.commit()
    flash("Conference deleted.", "info")
    return redirect(url_for("admin_conferences"))


@app.route("/admin/submissions")
@admin_required
def admin_submissions():
    conf_id = request.args.get("conference", type=int)
    dept_id = request.args.get("department", type=int)
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()

    query = Submission.query.join(Conference)
    if conf_id:
        query = query.filter(Submission.conference_id == conf_id)
    if dept_id:
        query = query.filter(Conference.department_id == dept_id)
    if status:
        query = query.filter(Submission.status == status)
    if q:
        query = query.filter(db.or_(Submission.paper_title.ilike(f"%{q}%"),
                                     Submission.abstract_id.ilike(f"%{q}%")))
    subs = query.order_by(Submission.submitted_at.desc()).all()
    conferences = Conference.query.order_by(Conference.name).all()
    departments = Department.query.order_by(Department.name).all()
    statuses = ["Submitted", "Under Review", "Accepted", "Rejected", "Revision Required", "Final Accepted"]
    return render_template("admin/submissions.html", submissions=subs, conferences=conferences,
                            departments=departments, statuses=statuses,
                            conf_id=conf_id, dept_id=dept_id, status=status, q=q)


@app.route("/admin/submissions/<int:sid>/update", methods=["POST"])
@admin_required
def admin_submission_update(sid):
    sub = Submission.query.get_or_404(sid)
    sub.status = request.form["status"]
    sub.reviewer_comments = request.form.get("reviewer_comments", "")
    db.session.commit()
    add_notification(sub.author_id, f"Submission status updated: {sub.status}",
                      f"Your paper '{sub.paper_title}' (Abstract ID {sub.abstract_id}) status is now '{sub.status}'.")
    db.session.commit()
    flash("Submission status updated.", "success")
    return redirect(url_for("admin_submissions"))


@app.route("/admin/authors")
@admin_required
def admin_authors():
    q = request.args.get("q", "").strip()
    query = Author.query
    if q:
        query = query.filter(db.or_(Author.name.ilike(f"%{q}%"), Author.email.ilike(f"%{q}%"),
                                     Author.author_code.ilike(f"%{q}%")))
    authors = query.order_by(Author.created_at.desc()).all()
    return render_template("admin/authors.html", authors=authors, q=q)


@app.route("/admin/authors/<int:aid>/verify", methods=["POST"])
@admin_required
def admin_author_verify(aid):
    author = Author.query.get_or_404(aid)
    author.verification_status = "Verified" if author.verification_status != "Verified" else "Pending"
    db.session.commit()
    flash(f"Author {author.author_code} marked as {author.verification_status}.", "success")
    return redirect(url_for("admin_authors"))


@app.route("/admin/reports")
@admin_required
def admin_reports():
    all_conf = Conference.query.all()
    dept_stats = []
    for d in Department.query.all():
        confs = [c for c in all_conf if c.department_id == d.id]
        subs = Submission.query.join(Conference).filter(Conference.department_id == d.id).count()
        dept_stats.append({"name": d.name, "conferences": len(confs), "submissions": subs})
    return render_template("admin/reports.html", dept_stats=dept_stats,
                            total_submissions=Submission.query.count(),
                            total_authors=Author.query.count(),
                            total_revenue=db.session.query(db.func.coalesce(db.func.sum(Registration.amount), 0)).filter_by(payment_status="Paid").scalar())


@app.route("/admin/reports/export/<kind>")
@admin_required
def admin_export_csv(kind):
    output = io.StringIO()
    writer = csv.writer(output)
    if kind == "submissions":
        writer.writerow(["Abstract ID", "Author", "Paper Title", "Conference", "Department",
                          "Presentation Type", "Submission Date", "Status"])
        for s in Submission.query.all():
            writer.writerow([s.abstract_id, s.author.name, s.paper_title, s.conference.name,
                              s.conference.department.name, s.presentation_type,
                              s.submitted_at.strftime("%Y-%m-%d"), s.status])
    elif kind == "authors":
        writer.writerow(["Author ID", "Name", "Email", "Institution", "Department", "Verification Status"])
        for a in Author.query.all():
            writer.writerow([a.author_code, a.name, a.email, a.institution, a.department, a.verification_status])
    elif kind == "payments":
        writer.writerow(["Registration ID", "Author", "Conference", "Amount", "Payment Status", "Payment ID"])
        for r in Registration.query.all():
            writer.writerow([r.registration_id, r.author.name, r.conference.name, r.amount,
                              r.payment_status, r.payment_id or ""])
    else:
        abort(404)

    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": f"attachment;filename={kind}_report.csv"})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
