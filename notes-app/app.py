from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from sqlite3 import Error
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your-secret-key"  # change in production
DB_PATH = "notes.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            created_at TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    conn = get_db_connection()
    notes = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("index.html", notes=notes)

@app.route("/add", methods=("GET", "POST"))
def add_note():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("add_note"))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO notes (title, content, created_at) VALUES (?, ?, ?)",
            (title, content, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        flash("Note added successfully!", "success")
        return redirect(url_for("index"))

    return render_template("add_note.html")

@app.route("/edit/<int:note_id>", methods=("GET", "POST"))
def edit_note(note_id):
    conn = get_db_connection()
    note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    if note is None:
        flash("Note not found.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("edit_note", note_id=note_id))

        conn = get_db_connection()
        conn.execute(
            "UPDATE notes SET title = ?, content = ? WHERE id = ?",
            (title, content, note_id)
        )
        conn.commit()
        conn.close()
        flash("Note updated successfully!", "success")
        return redirect(url_for("index"))

    return render_template("edit_note.html", note=note)

@app.route("/delete/<int:note_id>", methods=("POST",))
def delete_note(note_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    flash("Note deleted.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
