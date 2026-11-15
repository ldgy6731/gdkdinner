import os
import re
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Render 환경변수에 SECRET_KEY를 등록하는 것이 안전합니다.
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deploying")

# Render 영구 디스크를 연결하면 DATABASE_PATH를 /var/data/dinner.db로 설정합니다.
DATABASE_PATH = os.environ.get("DATABASE_PATH", "dinner.db")

DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")


def get_db():
    """SQLite 데이터베이스 연결을 반환합니다."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """필요한 데이터베이스 표를 처음 한 번 자동으로 만듭니다."""
    # 데이터베이스 폴더가 없으면 생성합니다.
    folder = os.path.dirname(DATABASE_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                check_time TEXT NOT NULL,
                check_date TEXT NOT NULL,
                UNIQUE(student_id, check_date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                suspected_student_id TEXT,
                content TEXT NOT NULL,
                report_time TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)

        # 최초 실행 시 관리자 비밀번호를 해시 형태로 저장합니다.
        row = conn.execute(
            "SELECT setting_value FROM settings WHERE setting_key = 'admin_password_hash'"
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO settings (setting_key, setting_value) VALUES (?, ?)",
                ("admin_password_hash", generate_password_hash(DEFAULT_ADMIN_PASSWORD))
            )


def admin_required(view):
    """관리자 로그인 여부를 확인하는 장식자입니다."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            flash("관리자 로그인이 필요합니다.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped_view


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/check", methods=["POST"])
def check_attendance():
    student_id = request.form.get("student_id", "").strip()

    if not re.fullmatch(r"\d{5}", student_id):
        flash("학번은 숫자 5자리로 입력해 주세요. 예: 20920", "error")
        return redirect(url_for("index"))

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        student = conn.execute(
            "SELECT student_id FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()

        if student is None:
            flash("등록되지 않은 학번입니다. 관리자에게 확인해 주세요.", "error")
            return redirect(url_for("index"))

        try:
            conn.execute(
                "INSERT INTO attendance (student_id, check_time, check_date) VALUES (?, ?, ?)",
                (student_id, now, today)
            )
            flash(f"{student_id} 출석 확인이 완료되었습니다.", "success")
        except sqlite3.IntegrityError:
            flash("오늘은 이미 출석 확인이 완료된 학번입니다.", "warning")

    return redirect(url_for("index"))


@app.route("/report", methods=["POST"])
def submit_report():
    category = request.form.get("category", "").strip()
    location = request.form.get("location", "").strip()
    suspected_student_id = request.form.get("suspected_student_id", "").strip()
    content = request.form.get("content", "").strip()

    allowed_categories = ["무단 석식 이용 의심 신고", "급식실 불편 사항"]

    if category not in allowed_categories:
        flash("제보 종류를 선택해 주세요.", "error")
        return redirect(url_for("index"))

    if not location or not content:
        flash("장소와 제보 내용을 모두 작성해 주세요.", "error")
        return redirect(url_for("index"))

    if suspected_student_id and not re.fullmatch(r"\d{5}", suspected_student_id):
        flash("관련 학번은 숫자 5자리로 입력하거나 비워 두세요.", "error")
        return redirect(url_for("index"))

    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO reports
               (category, location, suspected_student_id, content, report_time)
               VALUES (?, ?, ?, ?, ?)""",
            (category, location, suspected_student_id or None, content, report_time)
        )

    flash("제보가 익명으로 접수되었습니다. 사실에 근거해 작성해 주세요.", "success")
    return redirect(url_for("index"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")

        with get_db() as conn:
            row = conn.execute(
                "SELECT setting_value FROM settings WHERE setting_key = 'admin_password_hash'"
            ).fetchone()

        if row and check_password_hash(row["setting_value"], password):
            session.clear()
            session["is_admin"] = True
            flash("관리자 로그인에 성공했습니다.", "success")
            return redirect(url_for("admin_dashboard"))

        flash("비밀번호가 올바르지 않습니다.", "error")

    return render_template("admin_login.html")


@app.route("/admin", methods=["GET"])
@admin_required
def admin_dashboard():
    today = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        students = conn.execute(
            "SELECT student_id FROM students ORDER BY student_id"
        ).fetchall()
        attendance = conn.execute(
            """SELECT student_id, check_time FROM attendance
               WHERE check_date = ? ORDER BY check_time DESC""",
            (today,)
        ).fetchall()
        reports = conn.execute(
            "SELECT * FROM reports ORDER BY id DESC"
        ).fetchall()

    return render_template(
        "admin.html",
        students=students,
        attendance=attendance,
        reports=reports,
        today=today
    )


@app.route("/admin/students/add", methods=["POST"])
@admin_required
def add_students():
    raw_ids = request.form.get("student_ids", "")
    # 줄바꿈, 쉼표, 공백을 모두 구분자로 처리합니다.
    candidates = re.split(r"[\s,;]+", raw_ids.strip())
    valid_ids = sorted(set(item for item in candidates if item))

    if not valid_ids:
        flash("등록할 학번을 입력해 주세요.", "warning")
        return redirect(url_for("admin_dashboard"))

    invalid_ids = [item for item in valid_ids if not re.fullmatch(r"\d{5}", item)]
    valid_ids = [item for item in valid_ids if re.fullmatch(r"\d{5}", item)]

    added = 0
    with get_db() as conn:
        for student_id in valid_ids:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO students (student_id) VALUES (?)",
                (student_id,)
            )
            added += cursor.rowcount

    message = f"학번 {added}개를 새로 등록했습니다."
    if invalid_ids:
        message += " 형식이 맞지 않아 제외된 값: " + ", ".join(invalid_ids[:10])
    flash(message, "success" if added else "warning")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/students/delete", methods=["POST"])
@admin_required
def delete_student():
    student_id = request.form.get("student_id", "").strip()

    with get_db() as conn:
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))

    flash(f"{student_id} 학번을 학생 목록에서 삭제했습니다. 기존 출석 기록은 보존됩니다.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reports/delete", methods=["POST"])
@admin_required
def delete_report():
    report_id = request.form.get("report_id", "").strip()

    with get_db() as conn:
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))

    flash("선택한 제보를 삭제했습니다.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/password", methods=["POST"])
@admin_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    with get_db() as conn:
        row = conn.execute(
            "SELECT setting_value FROM settings WHERE setting_key = 'admin_password_hash'"
        ).fetchone()

        if not row or not check_password_hash(row["setting_value"], current_password):
            flash("현재 비밀번호가 올바르지 않습니다.", "error")
            return redirect(url_for("admin_dashboard"))

        if len(new_password) < 8:
            flash("새 비밀번호는 8자 이상으로 설정해 주세요.", "error")
            return redirect(url_for("admin_dashboard"))

        if new_password != confirm_password:
            flash("새 비밀번호가 서로 일치하지 않습니다.", "error")
            return redirect(url_for("admin_dashboard"))

        conn.execute(
            "UPDATE settings SET setting_value = ? WHERE setting_key = 'admin_password_hash'",
            (generate_password_hash(new_password),)
        )

    flash("관리자 비밀번호를 변경했습니다.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear()
    flash("로그아웃했습니다.", "success")
    return redirect(url_for("index"))


# 앱이 시작될 때 데이터베이스를 준비합니다.
init_db()

if __name__ == "__main__":
    app.run(debug=True)
