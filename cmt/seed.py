"""
Run this once to create the database tables and populate them with
realistic sample data (departments, conferences, admin, authors, submissions).

Usage:
    python seed.py
"""
import os
from datetime import date, timedelta, datetime
from werkzeug.security import generate_password_hash

from app import app, UPLOAD_DIR
from extensions import db
from models import (Admin, Department, Conference, Author, Submission,
                     Registration, Notification)


def make_sample_file(folder, filename, text):
    path = os.path.join(UPLOAD_DIR, folder, filename)
    with open(path, "w") as f:
        f.write(text)
    return filename


def run():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ---------------- Departments ----------------
        dept_data = [
            ("Computer Science & Engineering", "CSE"),
            ("Electronics & Communication Engineering", "ECE"),
            ("Mechanical Engineering", "MECH"),
            ("Civil Engineering", "CIVIL"),
            ("Information Technology", "IT"),
            ("Electrical Engineering", "EE"),
            ("Management", "MGT"),
            ("Other", "OTH"),
        ]
        departments = {}
        for name, code in dept_data:
            d = Department(name=name, code=code, description=f"Department of {name}, LJ University")
            db.session.add(d)
            db.session.flush()
            departments[code] = d

        # ---------------- Admin ----------------
        admin = Admin(name="CMT Administrator", email="admin@ljuniversity.edu.in",
                      password_hash=generate_password_hash("Admin@123"))
        db.session.add(admin)

        today = date.today()

        # ---------------- Conferences ----------------
        brochure_1 = make_sample_file("brochures", "icet_brochure.txt",
                                       "International Conference on Emerging Technologies - Brochure\nLJ University, IEEE Student Branch")
        flyer_1 = make_sample_file("flyers", "icet_flyer.txt", "ICET 2026 Flyer - LJ University")

        conferences = [
            Conference(
                name="International Conference on Emerging Technologies",
                department_id=departments["CSE"].id,
                description="ICET brings together researchers and practitioners to discuss the latest breakthroughs in emerging technologies including AI, IoT, and Cloud Computing.",
                objectives="To provide a platform for sharing cutting-edge research in emerging technologies and foster collaboration between academia and industry.",
                start_date=today + timedelta(days=60), end_date=today + timedelta(days=62),
                venue="LJ University Main Auditorium, Ahmedabad",
                registration_fee=1500,
                registration_deadline=today + timedelta(days=40),
                submission_deadline=today + timedelta(days=30),
                contact_email="icet@ljku.edu.in", contact_phone="+91 79 4890 0001",
                keynote_speakers="Dr. Anil Sharma, IIT Bombay\nProf. Meera Iyer, Stanford University",
                committee="Dr. Rakesh Patel - Conference Chair\nDr. Nisha Shah - Program Chair",
                schedule="Day 1: Inauguration & Keynote\nDay 2: Paper Presentations\nDay 3: Poster Session & Valedictory",
                brochure=brochure_1, flyer=flyer_1,
            ),
            Conference(
                name="National Conference on AI & Data Science",
                department_id=departments["CSE"].id,
                description="A national-level conference focused on advances in artificial intelligence, machine learning and data science applications.",
                objectives="To showcase innovative research in AI and Data Science from across the country.",
                start_date=today, end_date=today + timedelta(days=1),
                venue="LJ University Seminar Hall, Ahmedabad",
                registration_fee=1000,
                registration_deadline=today + timedelta(days=2),
                submission_deadline=today + timedelta(days=1),
                contact_email="ncaids@ljku.edu.in", contact_phone="+91 79 4890 0002",
                keynote_speakers="Dr. Kavita Rao, IISc Bangalore",
                committee="Dr. Sanjay Mehta - Conference Chair",
                schedule="Day 1: Keynotes & Technical Sessions\nDay 2: Panel Discussion & Awards",
            ),
            Conference(
                name="International Conference on Smart Engineering",
                department_id=departments["MECH"].id,
                description="Focused on smart manufacturing, robotics, and mechanical design innovations for Industry 4.0.",
                objectives="To bring together mechanical engineers and researchers working on smart engineering solutions.",
                start_date=today + timedelta(days=90), end_date=today + timedelta(days=92),
                venue="LJ University Engineering Block, Ahmedabad",
                registration_fee=1800,
                registration_deadline=today + timedelta(days=70),
                submission_deadline=today + timedelta(days=60),
                contact_email="icse@ljku.edu.in", contact_phone="+91 79 4890 0003",
                keynote_speakers="Dr. Ramesh Iyer, IIT Delhi",
                committee="Dr. Priya Desai - Conference Chair",
                schedule="Day 1: Inauguration\nDay 2: Technical Sessions\nDay 3: Industry Visit",
            ),
            Conference(
                name="Conference on Sustainable Infrastructure",
                department_id=departments["CIVIL"].id,
                description="A completed conference that explored sustainable construction practices, green building and urban infrastructure planning.",
                objectives="To discuss sustainable approaches to civil infrastructure development.",
                start_date=today - timedelta(days=120), end_date=today - timedelta(days=118),
                venue="LJ University Civil Block, Ahmedabad",
                registration_fee=1200,
                registration_deadline=today - timedelta(days=130),
                submission_deadline=today - timedelta(days=140),
                contact_email="csi@ljku.edu.in", contact_phone="+91 79 4890 0004",
                keynote_speakers="Dr. Alok Verma, CEPT University",
                committee="Dr. Kirti Trivedi - Conference Chair",
                schedule="Day 1: Keynote & Sessions\nDay 2: Site Visit & Closing",
            ),
            Conference(
                name="Electronics and Communication Innovation Summit",
                department_id=departments["ECE"].id,
                description="A summit dedicated to innovations in electronics, VLSI design, and wireless communication systems.",
                objectives="To provide a platform for ECE researchers to present novel work in communication systems.",
                start_date=today + timedelta(days=45), end_date=today + timedelta(days=46),
                venue="LJ University ECE Block, Ahmedabad",
                registration_fee=1300,
                registration_deadline=today + timedelta(days=30),
                submission_deadline=today + timedelta(days=20),
                contact_email="ecis@ljku.edu.in", contact_phone="+91 79 4890 0005",
                keynote_speakers="Dr. Neha Kulkarni, IIT Madras",
                committee="Dr. Vivek Joshi - Conference Chair",
                schedule="Day 1: Keynote, Sessions & Valedictory",
            ),
        ]
        for c in conferences:
            db.session.add(c)
        db.session.flush()

        # ---------------- Sample Authors ----------------
        authors_data = [
            ("Rohan Mehta", "rohan.mehta@example.com", "9less00011", "LJ University", "CSE", "Student", "India", "Ahmedabad"),
            ("Aisha Khan", "aisha.khan@example.com", "9less00022", "Nirma University", "ECE", "Research Scholar", "India", "Ahmedabad"),
            ("Vikram Singh", "vikram.singh@example.com", "9less00033", "LJ University", "MECH", "Faculty", "India", "Gandhinagar"),
            ("Priya Nair", "priya.nair@example.com", "9less00044", "GTU", "IT", "Student", "India", "Surat"),
        ]
        authors = []
        for i, (name, email, mobile, inst, dept, desig, country, city) in enumerate(authors_data, start=1):
            a = Author(
                author_code=f"AUT-{i:04d}", name=name, email=email,
                password_hash=generate_password_hash("Author@123"),
                mobile=mobile, institution=inst, department=dept, designation=desig,
                country=country, city=city, address=f"{city}, Gujarat, India",
                verification_status="Verified" if i % 2 == 0 else "Pending",
            )
            db.session.add(a)
            authors.append(a)
        db.session.flush()

        # ---------------- Sample Submissions ----------------
        sub_data = [
            (authors[0], conferences[0], "Deep Learning for Smart Traffic Management", "Submitted"),
            (authors[1], conferences[1], "Low-Power VLSI Design for IoT Devices", "Under Review"),
            (authors[2], conferences[2], "Robotics in Smart Manufacturing Lines", "Accepted"),
            (authors[3], conferences[0], "Cloud-Native Architectures for Scalable Web Apps", "Revision Required"),
            (authors[0], conferences[4], "5G Communication Systems: A Survey", "Final Accepted"),
        ]
        for i, (author, conf, title, status) in enumerate(sub_data, start=1):
            s = Submission(
                abstract_id=f"CMT-{datetime.now().year}-{i:04d}",
                author_id=author.id, conference_id=conf.id,
                paper_title=title,
                abstract=f"This paper presents a comprehensive study on {title.lower()}, exploring novel approaches and evaluating performance against existing benchmarks.",
                keywords="AI, Engineering, Innovation",
                presentation_type="Paper Presentation" if i % 2 else "Poster Presentation",
                status=status,
                reviewer_comments="Well-structured paper. Minor revisions suggested in methodology section." if status == "Revision Required" else "",
            )
            db.session.add(s)
            db.session.flush()
            db.session.add(Notification(author_id=author.id, title="Paper submitted successfully",
                                         message=f"Your paper '{title}' was submitted with Abstract ID {s.abstract_id}."))

        # ---------------- Sample Registrations ----------------
        for i, (author, conf) in enumerate([(authors[0], conferences[0]), (authors[2], conferences[2])], start=1):
            r = Registration(
                registration_id=f"REG-{i:05d}", author_id=author.id, conference_id=conf.id,
                amount=conf.registration_fee,
                payment_status="Paid" if i == 1 else "Pending",
                payment_id=f"PAY-{i:06d}" if i == 1 else None,
            )
            db.session.add(r)

        db.session.commit()
        print("Database seeded successfully!")
        print("Admin login -> email: admin@ljuniversity.edu.in | password: Admin@123")
        print("Sample author login -> email: rohan.mehta@example.com | password: Author@123")


if __name__ == "__main__":
    run()
