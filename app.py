
import os
import sqlite3
from datetime import datetime

from flask import Flask, request, render_template_string, redirect, url_for
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY is missing. Check your .env file."
    )

client = genai.Client(api_key=api_key)

DB_NAME = "practical_history.db"


# --------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


init_db()


# --------------------------------------------------
# COMMON HTML STYLES
# --------------------------------------------------

STYLE = """
<style>
    * { box-sizing: border-box; }

    body {
        margin: 0;
        padding: 25px;
        font-family: "Segoe UI", Arial, sans-serif;
        color: #292443;
        background: #f6f4fc;
    }

    .container {
        max-width: 1050px;
        margin: 20px auto;
    }

    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 15px;
        flex-wrap: wrap;
    }

    .brand {
        font-size: 25px;
        font-weight: 800;
        color: #30234f;
    }

    .brand span { color: #8065dc; }

    .muted { color: #77738c; line-height: 1.6; }

    .hero {
        margin-top: 28px;
        padding: 30px;
        border-radius: 20px;
        color: white;
        background: linear-gradient(120deg, #6350bd, #a083ed);
    }

    .hero h1 { margin-top: 0; font-size: 30px; }
    .hero p { line-height: 1.7; color: #f0eaff; }

    .card {
        margin-top: 22px;
        padding: 25px;
        background: white;
        border: 1px solid #ece8f7;
        border-radius: 16px;
        box-shadow: 0 5px 20px #33205b08;
    }

    input[type="text"] {
        width: 100%;
        min-width: 0;
        padding: 14px;
        border: 1px solid #ded8ef;
        border-radius: 10px;
        font-size: 15px;
        outline-color: #9477e7;
    }

    button, .link {
        display: inline-block;
        padding: 12px 16px;
        border: none;
        border-radius: 9px;
        background: #6b55c6;
        color: white;
        font-size: 14px;
        font-weight: 600;
        text-decoration: none;
        cursor: pointer;
    }

    button:hover, .link:hover { opacity: 0.88; }

    .dark { background: #30234f; }
    .light { background: #eee9ff; color: #5e48b3; }
    .danger { background: #fee9e9; color: #a52828; }

    .search-form {
        display: flex;
        gap: 10px;
        margin-top: 20px;
    }

    .answer {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        line-height: 1.8;
        margin-top: 18px;
    }

    .error {
        padding: 13px;
        background: #fff0f0;
        color: #a52828;
        border-radius: 9px;
        line-height: 1.6;
        overflow-wrap: anywhere;
    }

    .stats {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 15px;
        margin-top: 20px;
    }

    .stat {
        padding: 20px;
        border-radius: 14px;
        background: white;
        border: 1px solid #ece8f7;
    }

    .stat strong {
        display: block;
        font-size: 26px;
        color: #6b55c6;
        margin-bottom: 5px;
    }

    .topics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 15px;
        margin-top: 15px;
    }

    .topic-card {
        padding: 20px;
        border-radius: 14px;
        background: white;
        border: 1px solid #ece8f7;
    }

    .topic-card h3 { margin-top: 5px; }
    .topic-card p { color: #77738c; line-height: 1.6; font-size: 14px; }

    .topic-card form { margin-top: 10px; }
    .topic-card button { width: 100%; }

    .history-item {
        padding: 18px 0;
        border-bottom: 1px solid #eeeaf7;
    }

    .history-item:last-child { border-bottom: none; }
    .history-item h3 { margin: 0 0 8px; }

    .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 9px;
        margin-top: 12px;
    }

    .actions form { margin: 0; }

    footer {
        margin: 30px 0 10px;
        color: #89849e;
        text-align: center;
        font-size: 13px;
    }

    @media (max-width: 650px) {
        body { padding: 14px; }
        .hero { padding: 22px; }
        .search-form { flex-direction: column; }
        .stats, .topics { grid-template-columns: 1fr; }
    }
</style>
"""


# --------------------------------------------------
# DASHBOARD PAGE
# --------------------------------------------------

DASHBOARD_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PracticalAI - Exam Workspace</title>
    """ + STYLE + """
</head>
<body>
<div class="container">

    <div class="topbar">
        <div class="brand">✦ Practical<span>AI</span></div>
        <div>
            <a class="link dark" href="/">⌂ Dashboard</a>
            <a class="link" href="/history">◷ Study History</a>
        </div>
    </div>

    <section class="hero">
        <h1>Hey, let's get exam-ready! ✨</h1>
        <p>
            Your personal AI study assistant.
            Generate practical guides, revise concepts,
            and prepare for viva questions.
        </p>

        <form class="search-form" method="POST" action="/">
            <input type="text" name="topic" required
                   placeholder="Enter a topic, e.g. A* Search Algorithm"
                   value="{{ topic }}">
            <button class="dark" type="submit">✦ Generate Guide</button>
        </form>
    </section>

    <section class="stats">
        <div class="stat">
            <strong>{{ total }}</strong>
            Saved Guides
        </div>
        <div class="stat">
            <strong>AI</strong>
            Powered Study
        </div>
        <div class="stat">
            <strong>24/7</strong>
            Revision Space
        </div>
    </section>

    <h2>Explore practical topics</h2>
    <p class="muted">Choose a topic to start your revision.</p>

    <section class="topics">
        <div class="topic-card">
            <div>🧭</div>
            <h3>Search Algorithms</h3>
            <p>Learn how AI searches for paths and solutions.</p>
            <form method="POST" action="/">
                <input type="hidden" name="topic" value="A* Search Algorithm">
                <button class="light">A* Search →</button>
            </form>
            <form method="POST" action="/">
                <input type="hidden" name="topic" value="Best First Search">
                <button class="light">Best First Search →</button>
            </form>
        </div>

        <div class="topic-card">
            <div>🧠</div>
            <h3>Logic and Reasoning</h3>
            <p>Practice logical reasoning and decision-making.</p>
            <form method="POST" action="/">
                <input type="hidden" name="topic" value="Minimax Algorithm">
                <button class="light">Minimax Algorithm →</button>
            </form>
            <form method="POST" action="/">
                <input type="hidden" name="topic" value="Backward Chaining">
                <button class="light">Backward Chaining →</button>
            </form>
        </div>

        <div class="topic-card">
            <div>📊</div>
            <h3>Machine Learning</h3>
            <p>Revise useful machine learning algorithms.</p>
            <form method="POST" action="/">
                <input type="hidden" name="topic" value="K-Means Clustering">
                <button class="light">K-Means →</button>
            </form>
            <form method="POST" action="/">
                <input type="hidden" name="topic" value="K-Nearest Neighbors">
                <button class="light">KNN Algorithm →</button>
            </form>
        </div>
    </section>

    {% if answer %}
    <section class="card" id="guide">
        <p class="muted">YOUR GENERATED GUIDE</p>
        <h2>{{ topic }}</h2>
        <div class="answer">{{ answer }}</div>
        <p>
            <a class="link" href="/history">View saved guide in history →</a>
        </p>
    </section>
    {% endif %}

    {% if error %}
    <section class="card">
        <h2>Let's try again</h2>
        <p class="error">{{ error }}</p>
    </section>
    {% endif %}

    <footer>Made for curious minds · Study smarter, one practical at a time ✦</footer>
</div>
</body>
</html>
"""


# --------------------------------------------------
# HISTORY PAGE
# --------------------------------------------------

HISTORY_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PracticalAI - Study History</title>
    """ + STYLE + """
</head>
<body>
<div class="container">

    <div class="topbar">
        <div class="brand">✦ Practical<span>AI</span></div>
        <div>
            <a class="link dark" href="/">⌂ Dashboard</a>
            <a class="link" href="/history">◷ Study History</a>
        </div>
    </div>

    <section class="hero">
        <h1>📚 Your Study History</h1>
        <p>Your previously generated practical guides, all in one place.</p>
        <p><strong>{{ entries|length }}</strong> guide(s) shown</p>
    </section>

    <section class="card">
        <form method="GET" action="/history" class="search-form">
            <input type="text" name="q"
                   placeholder="Search saved topics..."
                   value="{{ query }}">
            <button type="submit">Search</button>
        </form>

        {% if entries %}
            {% for entry in entries %}
            <div class="history-item">
                <h3>{{ entry[1] }}</h3>
                <div class="muted">Saved on {{ entry[3] }}</div>
                <div class="actions">
                    <a class="link" href="/history/{{ entry[0] }}">Open Guide</a>
                    <form method="POST" action="/delete/{{ entry[0] }}"
                          onsubmit="return confirm('Delete this saved guide?');">
                        <button class="danger" type="submit">Delete</button>
                    </form>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <p class="muted">
                No matching guides found. Generate a guide from the dashboard
                to start building your history.
            </p>
        {% endif %}
    </section>

    <footer>Your progress is saved locally in your SQLite database.</footer>
</div>
</body>
</html>
"""


# --------------------------------------------------
# VIEW A SAVED GUIDE
# --------------------------------------------------

SAVED_GUIDE_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ entry[1] }} - PracticalAI</title>
    """ + STYLE + """
</head>
<body>
<div class="container">
    <div class="topbar">
        <div class="brand">✦ Practical<span>AI</span></div>
        <div>
            <a class="link dark" href="/">⌂ Dashboard</a>
            <a class="link" href="/history">◷ Study History</a>
        </div>
    </div>

    <section class="card">
        <p class="muted">SAVED PRACTICAL GUIDE · {{ entry[3] }}</p>
        <h1>{{ entry[1] }}</h1>
        <div class="answer">{{ entry[2] }}</div>
        <p>
            <a class="link" href="/history">← Back to History</a>
        </p>
    </section>
</div>
</body>
</html>
"""


# --------------------------------------------------
# GENERATE A NEW GUIDE
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def home():
    topic = ""
    answer = ""
    error = ""

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()

        if topic:
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=f"""
                    You are an AI Practical Exam Guide for a computer
                    engineering student.

                    Create a beginner-friendly practical guide for:
                    {topic}

                    Include:
                    1. Aim
                    2. Theory in simple words
                    3. Algorithm or steps
                    4. Code in a suitable programming language
                    5. Sample output and explanation
                    6. Five viva questions with short answers

                    Use clear headings and easy-to-understand explanations.
                    """
                )

                answer = response.text or "No text response was returned."

                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute(
                        """INSERT INTO history
                           (topic, answer, created_at)
                           VALUES (?, ?, ?)""",
                        (
                            topic,
                            answer,
                            datetime.now().strftime("%d-%m-%Y %I:%M %p")
                        )
                    )

            except Exception:
                app.logger.exception("Guide generation failed")
                error = (
                    "The guide could not be generated right now. "
                    "Please try again in a little while. "
                    "If the problem continues, check your Gemini model, "
                    "API key and internet connection. Failed requests "
                    "are not saved to history."
                )

    with sqlite3.connect(DB_NAME) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM history"
        ).fetchone()[0]

    return render_template_string(
        DASHBOARD_PAGE,
        topic=topic,
        answer=answer,
        error=error,
        total=total
    )


# --------------------------------------------------
# SEARCH AND VIEW HISTORY
# --------------------------------------------------

@app.route("/history")
def show_history():
    query = request.args.get("q", "").strip()

    with sqlite3.connect(DB_NAME) as conn:
        if query:
            entries = conn.execute(
                """SELECT id, topic, answer, created_at
                   FROM history
                   WHERE topic LIKE ?
                   ORDER BY id DESC""",
                (f"%{query}%",)
            ).fetchall()
        else:
            entries = conn.execute(
                """SELECT id, topic, answer, created_at
                   FROM history ORDER BY id DESC"""
            ).fetchall()

    return render_template_string(
        HISTORY_PAGE,
        entries=entries,
        query=query
    )


@app.route("/history/<int:entry_id>")
def view_history(entry_id):
    with sqlite3.connect(DB_NAME) as conn:
        entry = conn.execute(
            """SELECT id, topic, answer, created_at
               FROM history WHERE id = ?""",
            (entry_id,)
        ).fetchone()

    if entry is None:
        return "History entry not found.", 404

    return render_template_string(
        SAVED_GUIDE_PAGE,
        entry=entry
    )


# --------------------------------------------------
# DELETE A SAVED GUIDE
# --------------------------------------------------

@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete_history(entry_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "DELETE FROM history WHERE id = ?",
            (entry_id,)
        )

    return redirect(url_for("show_history"))


# --------------------------------------------------
# RUN THE APP
# --------------------------------------------------


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

