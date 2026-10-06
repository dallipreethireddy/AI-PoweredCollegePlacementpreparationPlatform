import streamlit as st
import subprocess
import tempfile
import os
import re
import sqlite3
import hashlib
import secrets
import random
import ollama
from pypdf import PdfReader

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Placement Preparation Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "placement_platform.db"


# ============================================================
# DATABASE - MULTIPLE USERS
# ============================================================

def get_db():
    return sqlite3.connect(DB_FILE)


def init_db():

    conn = get_db()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Student profiles
    cur.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            college TEXT,
            branch TEXT,
            year TEXT,
            skills TEXT,
            target_role TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Scores
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            user_id INTEGER PRIMARY KEY,
            aptitude_score INTEGER DEFAULT 0,
            dsa_score INTEGER DEFAULT 0,
            sql_score INTEGER DEFAULT 0,
            aptitude_completed INTEGER DEFAULT 0,
            dsa_completed INTEGER DEFAULT 0,
            sql_completed INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Interview history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            score INTEGER DEFAULT 0,
            interview_type TEXT,
            difficulty TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Coding attempts
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coding_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            language TEXT NOT NULL,
            question TEXT NOT NULL,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Roadmap progress
    cur.execute("""
        CREATE TABLE IF NOT EXISTS roadmap (
            user_id INTEGER NOT NULL,
            item_index INTEGER NOT NULL,
            completed INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, item_index),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# PASSWORD FUNCTIONS
# ============================================================

def hash_password(password, salt=None):

    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()

    return password_hash, salt


def verify_password(password, stored_hash, salt):

    password_hash, _ = hash_password(password, salt)

    return secrets.compare_digest(
        password_hash,
        stored_hash
    )


# ============================================================
# USER FUNCTIONS
# ============================================================

def register_user(username, password):

    username = username.strip()

    if not username or not password:
        return False, "Username and password are required."

    if len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if len(password) < 6:
        return False, "Password must contain at least 6 characters."

    password_hash, salt = hash_password(password)

    try:

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO users
            (username, password_hash, salt)
            VALUES (?, ?, ?)
            """,
            (
                username,
                password_hash,
                salt
            )
        )

        user_id = cur.lastrowid

        cur.execute(
            "INSERT INTO scores(user_id) VALUES (?)",
            (user_id,)
        )

        conn.commit()
        conn.close()

        return True, "Account created successfully."

    except sqlite3.IntegrityError:

        return False, "Username already exists. Please choose another username."

    except Exception as e:

        return False, f"Registration error: {e}"


def authenticate_user(username, password):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, username, password_hash, salt
        FROM users
        WHERE username = ?
        """,
        (username.strip(),)
    )

    row = cur.fetchone()

    conn.close()

    if row and verify_password(
        password,
        row[2],
        row[3]
    ):

        return {
            "id": row[0],
            "username": row[1]
        }

    return None


# ============================================================
# PROFILE DATABASE FUNCTIONS
# ============================================================

def get_profile(user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            name,
            email,
            college,
            branch,
            year,
            skills,
            target_role
        FROM profiles
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cur.fetchone()

    conn.close()

    if not row:
        return {}

    keys = [
        "name",
        "email",
        "college",
        "branch",
        "year",
        "skills",
        "target_role"
    ]

    return dict(zip(keys, row))


def save_profile(user_id, data):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO profiles
        (
            user_id,
            name,
            email,
            college,
            branch,
            year,
            skills,
            target_role
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            college=excluded.college,
            branch=excluded.branch,
            year=excluded.year,
            skills=excluded.skills,
            target_role=excluded.target_role
        """,
        (
            user_id,
            data["name"],
            data["email"],
            data["college"],
            data["branch"],
            data["year"],
            data["skills"],
            data["target_role"]
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# SCORE DATABASE FUNCTIONS
# ============================================================

def get_scores(user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            aptitude_score,
            dsa_score,
            sql_score,
            aptitude_completed,
            dsa_completed,
            sql_completed
        FROM scores
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cur.fetchone()

    conn.close()

    if not row:

        return {
            "aptitude_score": 0,
            "dsa_score": 0,
            "sql_score": 0,
            "aptitude_completed": False,
            "dsa_completed": False,
            "sql_completed": False
        }

    return {
        "aptitude_score": row[0],
        "dsa_score": row[1],
        "sql_score": row[2],
        "aptitude_completed": bool(row[3]),
        "dsa_completed": bool(row[4]),
        "sql_completed": bool(row[5])
    }


def save_score(
    user_id,
    field,
    score,
    completed=True
):

    allowed = {
        "aptitude": "aptitude_score",
        "dsa": "dsa_score",
        "sql": "sql_score"
    }

    if field not in allowed:
        return

    score_column = allowed[field]
    completed_column = f"{field}_completed"

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO scores(user_id) VALUES (?)",
        (user_id,)
    )

    cur.execute(
        f"""
        UPDATE scores
        SET
            {score_column} = ?,
            {completed_column} = ?
        WHERE user_id = ?
        """,
        (
            score,
            int(completed),
            user_id
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# INTERVIEW DATABASE FUNCTIONS
# ============================================================

def save_interview(
    user_id,
    question,
    answer,
    score,
    interview_type,
    difficulty
):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO interviews
        (
            user_id,
            question,
            answer,
            score,
            interview_type,
            difficulty
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            question,
            answer,
            score,
            interview_type,
            difficulty
        )
    )

    conn.commit()
    conn.close()


def get_interviews(user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            question,
            answer,
            score,
            interview_type,
            difficulty,
            created_at
        FROM interviews
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    )

    rows = cur.fetchall()

    conn.close()

    return rows


# ============================================================
# CODING DATABASE
# ============================================================

def save_coding_attempt(
    user_id,
    language,
    question,
    status
):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO coding_attempts
        (
            user_id,
            language,
            question,
            status
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            language,
            question,
            status
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# ROADMAP DATABASE
# ============================================================

def get_roadmap(user_id, count):

    conn = get_db()
    cur = conn.cursor()

    for i in range(count):

        cur.execute(
            """
            INSERT OR IGNORE INTO roadmap
            (
                user_id,
                item_index,
                completed
            )
            VALUES (?, ?, 0)
            """,
            (
                user_id,
                i
            )
        )

    conn.commit()

    cur.execute(
        """
        SELECT
            item_index,
            completed
        FROM roadmap
        WHERE user_id = ?
        ORDER BY item_index
        """,
        (user_id,)
    )

    rows = cur.fetchall()

    conn.close()

    return {
        i: bool(done)
        for i, done in rows
    }


def save_roadmap_item(
    user_id,
    index,
    completed
):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR REPLACE INTO roadmap
        (
            user_id,
            item_index,
            completed
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            index,
            int(completed)
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# SESSION STATE
# ============================================================

def reset_user_session():

    keys = [
        "aptitude_score",
        "aptitude_completed",
        "dsa_score",
        "dsa_completed",
        "sql_score",
        "sql_completed",
        "interview_question",
        "interview_score",
        "interview_feedback",
        "resume_text",
        "resume_analysis",
        "coding_question",
        "coding_language",
        "coding_code",
        "coding_attempt_status",
        "voice_answer"
    ]

    for key in keys:

        st.session_state.pop(
            key,
            None
        )


def load_user_data():

    user_id = st.session_state.current_user["id"]

    scores = get_scores(user_id)

    for key, value in scores.items():

        st.session_state[key] = value

    st.session_state.profile = get_profile(user_id)

    st.session_state.roadmap = get_roadmap(
        user_id,
        10
    )


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None


# ============================================================
# LOGIN / REGISTRATION PAGE
# ============================================================

def show_auth_page():

    st.title(
        "🎓 AI-Powered College Placement Preparation Platform"
    )

    st.write(
        "Create an account or login to access your personalized placement dashboard."
    )

    st.divider()

    login_tab, register_tab = st.tabs(
        [
            "🔐 Login",
            "📝 Register"
        ]
    )

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    with login_tab:

        st.subheader(
            "Student Login"
        )

        username = st.text_input(
            "Username",
            key="login_username"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "🔐 Login",
            use_container_width=True
        ):

            user = authenticate_user(
                username,
                password
            )

            if user:

                st.session_state.logged_in = True

                st.session_state.current_user = user

                reset_user_session()

                load_user_data()

                st.success(
                    f"Welcome, {user['username']}! 🎉"
                )

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

    # --------------------------------------------------------
    # REGISTRATION
    # --------------------------------------------------------

    with register_tab:

        st.subheader(
            "Create Student Account"
        )

        new_username = st.text_input(
            "Choose Username",
            key="register_username"
        )

        new_password = st.text_input(
            "Create Password",
            type="password",
            key="register_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="register_confirm"
        )

        if st.button(
            "📝 Create Account",
            use_container_width=True
        ):

            if new_password != confirm_password:

                st.error(
                    "Passwords do not match."
                )

            else:

                success, message = register_user(
                    new_username,
                    new_password
                )

                if success:

                    st.success(
                        message +
                        " You can now login."
                    )

                else:

                    st.error(message)

    st.info(
        "💡 Each student gets a separate profile, "
        "scores, interview history and roadmap progress."
    )


# ============================================================
# SHOW LOGIN IF NOT LOGGED IN
# ============================================================

if not st.session_state.logged_in:

    show_auth_page()

    st.stop()


# ============================================================
# CURRENT USER
# ============================================================

current_user = st.session_state.current_user

user_id = current_user["id"]

if "profile" not in st.session_state:

    load_user_data()


# ============================================================
# AI FUNCTION
# ============================================================

def ask_ai(prompt):

    response = ollama.chat(
        model="llama3.2:latest",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"].strip()


# ============================================================
# PYTHON CODE EXECUTION
# ============================================================

def run_python_code(code):

    file_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as file:

            file.write(code)

            file_path = file.name

        result = subprocess.run(
            [
                "python",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        return result

    except subprocess.TimeoutExpired:

        return None

    except FileNotFoundError:

        return "missing", None

    finally:

        if file_path and os.path.exists(file_path):

            try:

                os.remove(file_path)

            except Exception:

                pass


# ============================================================
# JAVA CODE EXECUTION
# ============================================================

def run_java_code(code):

    folder = tempfile.mkdtemp()

    java_file = os.path.join(
        folder,
        "Main.java"
    )

    try:

        with open(
            java_file,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(code)

        compile_result = subprocess.run(
            [
                "javac",
                java_file
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if compile_result.returncode != 0:

            return "compile", compile_result

        run_result = subprocess.run(
            [
                "java",
                "-cp",
                folder,
                "Main"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        return "run", run_result

    except FileNotFoundError:

        return "missing", None

    except subprocess.TimeoutExpired:

        return "timeout", None

    finally:

        try:

            for filename in os.listdir(folder):

                os.remove(
                    os.path.join(
                        folder,
                        filename
                    )
                )

            os.rmdir(folder)

        except Exception:

            pass


# ============================================================
# C++ CODE EXECUTION
# ============================================================

def run_cpp_code(code):

    folder = tempfile.mkdtemp()

    cpp_file = os.path.join(
        folder,
        "main.cpp"
    )

    exe_file = os.path.join(
        folder,
        "main.exe"
    )

    try:

        with open(
            cpp_file,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(code)

        compile_result = subprocess.run(
            [
                "g++",
                cpp_file,
                "-o",
                exe_file
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if compile_result.returncode != 0:

            return "compile", compile_result

        run_result = subprocess.run(
            [
                exe_file
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        return "run", run_result

    except FileNotFoundError:

        return "missing", None

    except subprocess.TimeoutExpired:

        return "timeout", None

    finally:

        try:

            for filename in os.listdir(folder):

                os.remove(
                    os.path.join(
                        folder,
                        filename
                    )
                )

            os.rmdir(folder)

        except Exception:

            pass


# ============================================================
# TEXT TO SPEECH
# ============================================================

def text_to_speech(text):

    if pyttsx3 is None:

        return None

    audio_path = None

    try:

        engine = pyttsx3.init()

        engine.setProperty(
            "rate",
            165
        )

        engine.setProperty(
            "volume",
            1.0
        )

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as temp:

            audio_path = temp.name

        engine.save_to_file(
            text,
            audio_path
        )

        engine.runAndWait()

        if (
            not os.path.exists(audio_path)
            or
            os.path.getsize(audio_path) == 0
        ):

            return None

        with open(
            audio_path,
            "rb"
        ) as audio_file:

            audio_bytes = audio_file.read()

        return audio_bytes

    except Exception:

        return None

    finally:

        if (
            audio_path
            and
            os.path.exists(audio_path)
        ):

            try:

                os.remove(audio_path)

            except Exception:

                pass


# ============================================================
# SPEECH TO TEXT
# ============================================================

def transcribe_audio(uploaded_audio):

    if sr is None:

        return None, (
            "SpeechRecognition is not installed."
        )

    audio_path = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as temp:

            temp.write(
                uploaded_audio.getvalue()
            )

            audio_path = temp.name

        recognizer = sr.Recognizer()

        with sr.AudioFile(
            audio_path
        ) as source:

            audio_data = recognizer.record(
                source
            )

        text = recognizer.recognize_google(
            audio_data
        )

        return text, None

    except sr.UnknownValueError:

        return None, (
            "I could not understand the recording. "
            "Please speak clearly and try again."
        )

    except sr.RequestError as e:

        return None, (
            f"Speech recognition service is unavailable: {e}"
        )

    except Exception as e:

        return None, str(e)

    finally:

        if (
            audio_path
            and
            os.path.exists(audio_path)
        ):

            try:

                os.remove(audio_path)

            except Exception:

                pass


# ============================================================
# CODING QUESTION BANK
# ============================================================

CODING_QUESTIONS = {

    "Python": [

        {
            "title": "Find the Largest Number",
            "difficulty": "Easy",
            "question": (
                "Write a program to find the largest "
                "number in a list."
            ),
            "code": """numbers = [10, 25, 7, 40, 15]

# Write your code here
"""
        },

        {
            "title": "Check Even or Odd",
            "difficulty": "Easy",
            "question": (
                "Write a program to check whether "
                "a number is even or odd."
            ),
            "code": """number = 10

# Write your code here
"""
        },

        {
            "title": "Reverse a String",
            "difficulty": "Easy",
            "question": (
                "Write a program to reverse a given "
                "string without using reversed()."
            ),
            "code": """text = "placement"

# Write your code here
"""
        },

        {
            "title": "Count Vowels",
            "difficulty": "Easy",
            "question": (
                "Write a program to count the number "
                "of vowels in a string."
            ),
            "code": """text = "data science"

# Write your code here
"""
        },

        {
            "title": "Find Second Largest",
            "difficulty": "Medium",
            "question": (
                "Find the second largest distinct number "
                "in a list without sorting the list."
            ),
            "code": """numbers = [10, 5, 20, 8, 20, 15]

# Write your code here
"""
        },

        {
            "title": "Remove Duplicates",
            "difficulty": "Medium",
            "question": (
                "Remove duplicate values from a list "
                "while preserving the original order."
            ),
            "code": """numbers = [1, 2, 2, 3, 1, 4, 3]

# Write your code here
"""
        },

        {
            "title": "Two Sum",
            "difficulty": "Medium",
            "question": (
                "Find two numbers whose sum equals a "
                "target value and print their indices."
            ),
            "code": """numbers = [2, 7, 11, 15]
target = 9

# Write your code here
"""
        },

        {
            "title": "Palindrome Check",
            "difficulty": "Medium",
            "question": (
                "Check whether a given string is a palindrome."
            ),
            "code": """text = "madam"

# Write your code here
"""
        },

        {
            "title": "Frequency of Elements",
            "difficulty": "Medium",
            "question": (
                "Count how many times each element occurs "
                "in a list."
            ),
            "code": """numbers = [1, 2, 2, 3, 3, 3, 4]

# Write your code here
"""
        },

        {
            "title": "Fibonacci Series",
            "difficulty": "Easy",
            "question": (
                "Print the first 10 numbers of the "
                "Fibonacci series."
            ),
            "code": """# Write your code here
"""
        }

    ],

    "Java": [

        {
            "title": "Find the Largest Number",
            "difficulty": "Easy",
            "question": (
                "Write a Java program to find the largest "
                "number in an integer array."
            ),
            "code": """public class Main {

    public static void main(String[] args) {

        int[] numbers = {10, 25, 7, 40, 15};

        // Write your code here

    }
}
"""
        },

        {
            "title": "Even or Odd",
            "difficulty": "Easy",
            "question": (
                "Write a Java program to check whether "
                "a number is even or odd."
            ),
            "code": """public class Main {

    public static void main(String[] args) {

        int number = 10;

        // Write your code here

    }
}
"""
        },

        {
            "title": "Reverse a String",
            "difficulty": "Easy",
            "question": (
                "Write a Java program to reverse a string."
            ),
            "code": """public class Main {

    public static void main(String[] args) {

        String text = "placement";

        // Write your code here

    }
}
"""
        },

        {
            "title": "Sum of Array",
            "difficulty": "Easy",
            "question": (
                "Write a Java program to calculate "
                "the sum of all elements in an array."
            ),
            "code": """public class Main {

    public static void main(String[] args) {

        int[] numbers = {10, 20, 30, 40};

        // Write your code here

    }
}
"""
        },

        {
            "title": "Second Largest",
            "difficulty": "Medium",
            "question": (
                "Find the second largest distinct element "
                "in an integer array without sorting."
            ),
            "code": """public class Main {

    public static void main(String[] args) {

        int[] numbers = {10, 5, 20, 8, 20, 15};

        // Write your code here

    }
}
"""
        },

        {
            "title": "Palindrome String",
            "difficulty": "Medium",
            "question": (
                "Check whether a string is a palindrome."
            ),
            "code": """public class Main {

    public static void main(String[] args) {

        String text = "madam";

        // Write your code here

    }
}
"""
        },

        {
            "title": "Count Vowels",
            "difficulty": "Easy",
            "question": (
                "Count the number of vowels in a string."
            ),
            "code": """public class Main {

    public static void main(String[] args) {

        String text = "data science";

        // Write your code here

    }
}
"""
        },

        {
            "title": "Linear Search",
            "difficulty": "Easy",
            "question": (
                "Search for a target element in an array "
                "using linear search."
            ),
            "code": """public class Main {

    public static void main(String[] args) {

        int[] numbers = {10, 20, 30, 40, 50};

        int target = 30;

        // Write your code here

    }
}
"""
        }

    ],

    "C++": [

        {
            "title": "Find the Largest Number",
            "difficulty": "Easy",
            "question": (
                "Write a C++ program to find the largest "
                "number in an array."
            ),
            "code": """#include <iostream>

using namespace std;

int main() {

    int numbers[] = {10, 25, 7, 40, 15};

    // Write your code here

    return 0;
}
"""
        },

        {
            "title": "Even or Odd",
            "difficulty": "Easy",
            "question": (
                "Write a C++ program to check whether "
                "a number is even or odd."
            ),
            "code": """#include <iostream>

using namespace std;

int main() {

    int number = 10;

    // Write your code here

    return 0;
}
"""
        },

        {
            "title": "Reverse a String",
            "difficulty": "Easy",
            "question": (
                "Write a C++ program to reverse a string."
            ),
            "code": """#include <iostream>
#include <string>

using namespace std;

int main() {

    string text = "placement";

    // Write your code here

    return 0;
}
"""
        },

        {
            "title": "Sum of Array",
            "difficulty": "Easy",
            "question": (
                "Calculate and print the sum of all "
                "elements in an array."
            ),
            "code": """#include <iostream>

using namespace std;

int main() {

    int numbers[] = {10, 20, 30, 40};

    // Write your code here

    return 0;
}
"""
        },

        {
            "title": "Second Largest",
            "difficulty": "Medium",
            "question": (
                "Find the second largest distinct element "
                "without sorting the array."
            ),
            "code": """#include <iostream>

using namespace std;

int main() {

    int numbers[] = {10, 5, 20, 8, 20, 15};

    // Write your code here

    return 0;
}
"""
        },

        {
            "title": "Palindrome String",
            "difficulty": "Medium",
            "question": (
                "Check whether a string is a palindrome."
            ),
            "code": """#include <iostream>
#include <string>

using namespace std;

int main() {

    string text = "madam";

    // Write your code here

    return 0;
}
"""
        },

        {
            "title": "Linear Search",
            "difficulty": "Easy",
            "question": (
                "Search for a target element in an array "
                "using linear search."
            ),
            "code": """#include <iostream>

using namespace std;

int main() {

    int numbers[] = {10, 20, 30, 40, 50};

    int target = 30;

    // Write your code here

    return 0;
}
"""
        },

        {
            "title": "Factorial",
            "difficulty": "Easy",
            "question": (
                "Write a program to calculate the "
                "factorial of a number."
            ),
            "code": """#include <iostream>

using namespace std;

int main() {

    int n = 5;

    // Write your code here

    return 0;
}
"""
        }

    ]

}


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🎓 Placement Platform"
)

st.sidebar.caption(
    "AI-Powered College Placement Preparation"
)

st.sidebar.success(
    f"👤 Logged in: {current_user['username']}"
)

st.sidebar.divider()


page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "👤 Student Profile",
        "📚 Aptitude Practice",
        "💻 Coding Practice",
        "🤖 AI Mock Interview",
        "📄 Resume Analyzer",
        "🧠 DSA Practice",
        "🗄️ SQL Practice",
        "💬 AI Placement Assistant",
        "🎯 Placement Roadmap",
        "📊 Progress"
    ]
)


st.sidebar.divider()

st.sidebar.success(
    "🤖 AI Model: Llama 3.2"
)


if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True
):

    st.session_state.logged_in = False

    st.session_state.current_user = None

    reset_user_session()

    st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title(
        "🎓 AI-Powered College Placement Preparation Platform"
    )

    student_name = (
        st.session_state.profile.get("name")
        or
        current_user["username"]
    )

    st.write(
        f"Welcome, **{student_name}**! 👋"
    )

    st.write(
        "An all-in-one platform to help students "
        "prepare for technical and non-technical "
        "placement interviews."
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "📚 Aptitude",
            f"{st.session_state.aptitude_score}/5"
        )

    with col2:

        st.metric(
            "💻 Coding",
            "Random Questions"
        )

    with col3:

        st.metric(
            "🤖 Interviews",
            len(get_interviews(user_id))
        )

    with col4:

        st.metric(
            "🧠 DSA",
            f"{st.session_state.dsa_score}/5"
        )

    st.divider()

    st.subheader(
        "🚀 Platform Features"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown("""
### 👥 Multiple Users

- Student registration
- Secure login
- Individual profiles
- Separate progress tracking
""")

        st.markdown("""
### 📚 Aptitude

- Quantitative aptitude
- Logical reasoning
- MCQ practice
- Score calculation
- Retake test
""")

        st.markdown("""
### 💻 Coding

- Multiple questions
- Random question selection
- Python
- Java
- C++
- Difficulty selection
- Code execution
""")

    with col2:

        st.markdown("""
### 🤖 AI Interview

- Technical interview
- HR interview
- Mixed interview
- Random AI questions
- Text answers
- Voice answers
- Voice question playback
- AI evaluation
""")

        st.markdown("""
### 📄 Resume Analyzer

- PDF upload
- Text extraction
- Skill detection
- AI feedback
- Improvement suggestions
""")

    with col3:

        st.markdown("""
### 🧠 DSA Practice

- Arrays
- Strings
- Searching
- Sorting
- AI explanations
""")

        st.markdown("""
### 🗄️ SQL Practice

- SQL MCQs
- Query practice
- Score tracking
""")

        st.markdown("""
### 📊 Personalized Progress

- Test scores
- Interview history
- Roadmap progress
- User-specific data
""")

    st.divider()

    st.info(
        "💡 Each registered student has separate data. "
        "Coding questions are selected randomly from the question bank."
    )


# ============================================================
# STUDENT PROFILE
# ============================================================

elif page == "👤 Student Profile":

    st.title(
        "👤 Student Profile"
    )

    st.write(
        "Create and update your placement preparation profile."
    )

    profile = st.session_state.profile

    branches = [
        "Data Science",
        "Computer Science",
        "Information Technology",
        "Artificial Intelligence",
        "Electronics",
        "Other"
    ]

    years = [
        "1st Year",
        "2nd Year",
        "3rd Year",
        "4th Year"
    ]

    roles = [
        "Data Scientist",
        "Data Analyst",
        "Software Developer",
        "Python Developer",
        "AI/ML Engineer",
        "Full Stack Developer"
    ]

    name = st.text_input(
        "Student Name",
        value=profile.get(
            "name",
            ""
        )
    )

    email = st.text_input(
        "Email",
        value=profile.get(
            "email",
            ""
        )
    )

    college = st.text_input(
        "College Name",
        value=profile.get(
            "college",
            ""
        )
    )

    branch_default = profile.get(
        "branch",
        "Data Science"
    )

    branch_index = (
        branches.index(branch_default)
        if branch_default in branches
        else 0
    )

    branch = st.selectbox(
        "Branch",
        branches,
        index=branch_index
    )

    year_default = profile.get(
        "year",
        "2nd Year"
    )

    year_index = (
        years.index(year_default)
        if year_default in years
        else 1
    )

    year = st.selectbox(
        "Year",
        years,
        index=year_index
    )

    skills = st.text_area(
        "Skills",
        value=profile.get(
            "skills",
            ""
        ),
        placeholder=(
            "Python, Java, SQL, Machine Learning..."
        )
    )

    role_default = profile.get(
        "target_role",
        "Data Scientist"
    )

    role_index = (
        roles.index(role_default)
        if role_default in roles
        else 0
    )

    target_role = st.selectbox(
        "Target Job Role",
        roles,
        index=role_index
    )

    if st.button(
        "💾 Save Profile"
    ):

        if name.strip():

            save_profile(
                user_id,
                {
                    "name": name.strip(),
                    "email": email.strip(),
                    "college": college.strip(),
                    "branch": branch,
                    "year": year,
                    "skills": skills.strip(),
                    "target_role": target_role
                }
            )

            st.session_state.profile = get_profile(
                user_id
            )

            st.success(
                f"Profile saved successfully for {name}! 🎉"
            )

        else:

            st.warning(
                "Please enter your name."
            )


# ============================================================
# APTITUDE PRACTICE
# ============================================================

elif page == "📚 Aptitude Practice":

    st.title(
        "📚 Aptitude Practice"
    )

    st.write(
        "Test your quantitative aptitude and logical reasoning."
    )

    questions = [

        {
            "q": "What is 20% of 150?",
            "options": [
                "20",
                "25",
                "30",
                "35"
            ],
            "answer": "30"
        },

        {
            "q": "What is 5 + 3 × 2?",
            "options": [
                "16",
                "11",
                "13",
                "10"
            ],
            "answer": "11"
        },

        {
            "q": (
                "A train travels at 60 km/h for "
                "3 hours. What distance does it cover?"
            ),
            "options": [
                "120 km",
                "150 km",
                "180 km",
                "200 km"
            ],
            "answer": "180 km"
        },

        {
            "q": (
                "What is the average of 10, 20 and 30?"
            ),
            "options": [
                "15",
                "20",
                "25",
                "30"
            ],
            "answer": "20"
        },

        {
            "q": (
                "A product costs ₹500 and has a "
                "10% discount. What is the final price?"
            ),
            "options": [
                "₹400",
                "₹450",
                "₹475",
                "₹490"
            ],
            "answer": "₹450"
        }

    ]

    selected_answers = []

    for i, question in enumerate(
        questions
    ):

        answer = st.radio(
            f"{i + 1}. {question['q']}",
            question["options"],
            key=f"aptitude_{user_id}_{i}"
        )

        selected_answers.append(
            answer
        )

    st.divider()

    if st.button(
        "📝 Submit Test"
    ):

        score = sum(
            selected_answers[i]
            == questions[i]["answer"]
            for i in range(
                len(questions)
            )
        )

        save_score(
            user_id,
            "aptitude",
            score
        )

        st.session_state.aptitude_score = score
        st.session_state.aptitude_completed = True

        st.success(
            f"🎉 Your score is {score}/5"
        )

    if st.session_state.aptitude_completed:

        score = st.session_state.aptitude_score

        if score == 5:

            st.success(
                "🌟 Excellent performance!"
            )

        elif score >= 3:

            st.info(
                "👍 Good job! Keep practicing."
            )

        else:

            st.warning(
                "💪 Practice more to improve your score."
            )

        if st.button(
            "🔄 Retake Test"
        ):

            save_score(
                user_id,
                "aptitude",
                0,
                False
            )

            st.session_state.aptitude_score = 0

            st.session_state.aptitude_completed = False

            st.rerun()


# ============================================================
# CODING PRACTICE
# MULTIPLE + RANDOM QUESTIONS
# ============================================================

elif page == "💻 Coding Practice":

    st.title(
        "💻 Coding Practice"
    )

    st.write(
        "Practice multiple placement coding problems "
        "with random question selection."
    )

    st.success(
        "🎲 Random Question Bank Enabled — "
        "every new question can be different."
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        language = st.selectbox(
            "Programming Language",
            [
                "Python",
                "Java",
                "C++"
            ],
            key="coding_language_select"
        )

    with col2:

        difficulty = st.selectbox(
            "Difficulty",
            [
                "All",
                "Easy",
                "Medium"
            ],
            key="coding_difficulty_select"
        )

    with col3:

        if st.button(
            "🎲 New Random Question",
            use_container_width=True
        ):

            candidates = CODING_QUESTIONS[
                language
            ]

            if difficulty != "All":

                filtered = [
                    q
                    for q in candidates
                    if q["difficulty"]
                    == difficulty
                ]

                candidates = (
                    filtered
                    or
                    candidates
                )

            question = random.choice(
                candidates
            )

            st.session_state.coding_question = question

            st.session_state.coding_language = language

            st.session_state.coding_code = question[
                "code"
            ]

            st.session_state.coding_attempt_status = ""

            st.rerun()

    # Automatically select first random question
    if (
        "coding_question"
        not in st.session_state
        or
        st.session_state.get(
            "coding_language"
        ) != language
    ):

        candidates = CODING_QUESTIONS[
            language
        ]

        if difficulty != "All":

            filtered = [
                q
                for q in candidates
                if q["difficulty"]
                == difficulty
            ]

            candidates = (
                filtered
                or
                candidates
            )

        st.session_state.coding_question = random.choice(
            candidates
        )

        st.session_state.coding_language = language

        st.session_state.coding_code = (
            st.session_state.coding_question[
                "code"
            ]
        )

    question = st.session_state.coding_question

    st.divider()

    st.subheader(
        f"🧩 {question['title']}"
    )

    st.caption(
        f"Difficulty: {question['difficulty']} | "
        f"Language: {language}"
    )

    st.info(
        question["question"]
    )

    code = st.text_area(
        "Write your code:",
        key="coding_code",
        height=380
    )

    if st.button(
        "▶️ Run Code",
        type="primary"
    ):

        status_for_db = "Error"

        # ----------------------------------------------------
        # PYTHON
        # ----------------------------------------------------

        if language == "Python":

            result = run_python_code(
                code
            )

            if (
                isinstance(result, tuple)
                and
                result[0] == "missing"
            ):

                st.error(
                    "❌ Python was not found in PATH."
                )

            elif result is None:

                st.error(
                    "⏱️ Code execution timed out."
                )

            elif result.returncode == 0:

                status_for_db = "Success"

                st.success(
                    "✅ Python code executed successfully!"
                )

                st.subheader(
                    "📤 Output"
                )

                st.code(
                    result.stdout
                    if result.stdout
                    else "No output"
                )

            else:

                st.error(
                    "❌ Python error"
                )

                st.code(
                    result.stderr
                )

        # ----------------------------------------------------
        # JAVA
        # ----------------------------------------------------

        elif language == "Java":

            status, result = run_java_code(
                code
            )

            if status == "missing":

                st.warning(
                    "⚠️ Java compiler (javac) "
                    "is not installed or not in PATH."
                )

            elif status == "compile":

                st.error(
                    "❌ Java compilation error"
                )

                st.code(
                    result.stderr
                )

            elif status == "timeout":

                st.error(
                    "⏱️ Java execution timed out."
                )

            elif result.returncode == 0:

                status_for_db = "Success"

                st.success(
                    "✅ Java code executed successfully!"
                )

                st.code(
                    result.stdout
                    if result.stdout
                    else "No output"
                )

            else:

                st.error(
                    "❌ Java runtime error"
                )

                st.code(
                    result.stderr
                )

        # ----------------------------------------------------
        # C++
        # ----------------------------------------------------

        else:

            status, result = run_cpp_code(
                code
            )

            if status == "missing":

                st.warning(
                    "⚠️ g++ compiler is not installed or not in PATH."
                )

            elif status == "compile":

                st.error(
                    "❌ C++ compilation error"
                )

                st.code(
                    result.stderr
                )

            elif status == "timeout":

                st.error(
                    "⏱️ C++ execution timed out."
                )

            elif result.returncode == 0:

                status_for_db = "Success"

                st.success(
                    "✅ C++ code executed successfully!"
                )

                st.code(
                    result.stdout
                    if result.stdout
                    else "No output"
                )

            else:

                st.error(
                    "❌ C++ runtime error"
                )

                st.code(
                    result.stderr
                )

        save_coding_attempt(
            user_id,
            language,
            question["question"],
            status_for_db
        )

        st.session_state.coding_attempt_status = (
            status_for_db
        )

    st.divider()

    st.subheader(
        "📚 Available Question Bank"
    )

    st.write(
        f"**{len(CODING_QUESTIONS[language])} "
        f"questions** available for {language}."
    )

    for item in CODING_QUESTIONS[language]:

        st.write(
            f"• {item['title']} — "
            f"{item['difficulty']}"
        )


# ============================================================
# AI MOCK INTERVIEW
# TEXT + VOICE
# ============================================================

elif page == "🤖 AI Mock Interview":

    st.title(
        "🤖 AI Mock Interview"
    )

    st.write(
        "Practice technical and HR interviews "
        "with your local AI interviewer."
    )

    st.success(
        "🤖 Powered by Ollama + Llama 3.2 | "
        "🎤 Voice Interview Enabled"
    )

    col1, col2 = st.columns(2)

    with col1:

        interview_type = st.selectbox(
            "Interview Type",
            [
                "Technical",
                "HR",
                "Mixed"
            ],
            key="interview_type"
        )

    with col2:

        difficulty = st.selectbox(
            "Difficulty",
            [
                "Beginner",
                "Intermediate",
                "Advanced"
            ],
            key="interview_difficulty"
        )

    if st.button(
        "🎤 Generate Interview Question",
        type="primary"
    ):

        try:

            if interview_type == "Technical":

                topics = """
Python, Java, SQL, Data Structures,
Algorithms, DBMS, Operating Systems,
OOP and Data Science.
"""

            elif interview_type == "HR":

                topics = """
self introduction, strengths,
weaknesses, teamwork, leadership,
career goals, conflict handling
and company motivation.
"""

            else:

                topics = """
Mix technical and HR interview topics.
"""

            prompt = f"""
You are an experienced college placement interviewer.

Generate ONE interview question.

Interview Type:
{interview_type}

Difficulty:
{difficulty}

Topics:
{topics}

Rules:

1. Ask only one question.
2. Do not give the answer.
3. Keep it suitable for a B.Tech student.
4. Make it realistic for a placement interview.
5. Do not repeat a common question if possible.
"""

            st.session_state.interview_question = ask_ai(
                prompt
            )

            st.session_state.interview_feedback = ""

            st.session_state.interview_score = 0

        except Exception as e:

            st.error(
                "❌ Could not connect to Ollama."
            )

            st.code(
                str(e)
            )

    # --------------------------------------------------------
    # DISPLAY QUESTION
    # --------------------------------------------------------

    if st.session_state.get(
        "interview_question"
    ):

        st.divider()

        st.subheader(
            "🎤 Interview Question"
        )

        st.info(
            st.session_state.interview_question
        )

        # ----------------------------------------------------
        # VOICE OUTPUT
        # ----------------------------------------------------

        if st.button(
            "🔊 Listen to Question"
        ):

            with st.spinner(
                "Generating voice..."
            ):

                audio_bytes = text_to_speech(
                    st.session_state.interview_question
                )

            if audio_bytes:

                st.audio(
                    audio_bytes,
                    format="audio/wav"
                )

            else:

                st.warning(
                    "Voice output could not be generated. "
                    "You can still read the question above."
                )

        # ----------------------------------------------------
        # TEXT ANSWER
        # ----------------------------------------------------

        st.subheader(
            "📝 Answer the Interview Question"
        )

        answer = st.text_area(
            "Type your answer:",
            value=st.session_state.get(
                "voice_answer",
                ""
            ),
            height=180,
            key="interview_text_answer",
            placeholder=(
                "You can type your answer "
                "or use the microphone below."
            )
        )

        # ----------------------------------------------------
        # VOICE ANSWER
        # ----------------------------------------------------

        st.markdown(
            "### 🎤 Voice Answer"
        )

        st.caption(
            "Click the microphone, speak your answer, "
            "stop recording, and the platform will "
            "convert your speech to text."
        )

        audio_input = st.audio_input(
            "🎙️ Record your answer"
        )

        if audio_input is not None:

            with st.spinner(
                "Converting your voice to text..."
            ):

                transcribed, error = transcribe_audio(
                    audio_input
                )

            if transcribed:

                st.session_state.voice_answer = (
                    transcribed
                )

                st.success(
                    "✅ Voice converted to text."
                )

                st.text_area(
                    "🗣️ Transcribed Answer",
                    value=transcribed,
                    height=150,
                    key="transcribed_preview"
                )

                answer = transcribed

            elif error:

                st.warning(
                    error
                )

        # ----------------------------------------------------
        # EVALUATE
        # ----------------------------------------------------

        if st.button(
            "📊 Evaluate Answer",
            type="primary"
        ):

            final_answer = (
                st.session_state.get(
                    "voice_answer",
                    ""
                )
                if not answer.strip()
                else answer.strip()
            )

            if not final_answer:

                st.warning(
                    "Please type an answer or "
                    "record a voice answer."
                )

            else:

                try:

                    evaluation_prompt = f"""
You are a professional placement interviewer.

Evaluate this student's answer.

QUESTION:

{st.session_state.interview_question}


STUDENT ANSWER:

{final_answer}


Give the response in exactly this format:


SCORE: X/10

STRENGTHS:

- Strength 1
- Strength 2

WEAKNESSES:

- Weakness 1
- Weakness 2

FEEDBACK:

Explain how the student can improve.

IMPROVED ANSWER:

Give a better sample answer.

Be encouraging and suitable for a college student.
"""

                    with st.spinner(
                        "🤖 AI is evaluating your answer..."
                    ):

                        evaluation = ask_ai(
                            evaluation_prompt
                        )

                    st.session_state.interview_feedback = (
                        evaluation
                    )

                    score_match = re.search(
                        r"SCORE:\s*(\d+)\s*/\s*10",
                        evaluation,
                        re.IGNORECASE
                    )

                    if score_match:

                        score = int(
                            score_match.group(1)
                        )

                    else:

                        score = 0

                    score = min(
                        max(score, 0),
                        10
                    )

                    st.session_state.interview_score = (
                        score
                    )

                    save_interview(
                        user_id,
                        st.session_state.interview_question,
                        final_answer,
                        score,
                        interview_type,
                        difficulty
                    )

                    st.session_state.voice_answer = ""

                except Exception as e:

                    st.error(
                        "❌ AI evaluation failed."
                    )

                    st.code(
                        str(e)
                    )

        # ----------------------------------------------------
        # DISPLAY EVALUATION
        # ----------------------------------------------------

        if st.session_state.get(
            "interview_feedback"
        ):

            st.divider()

            st.subheader(
                "⭐ Evaluation"
            )

            st.metric(
                "Interview Score",
                f"{st.session_state.interview_score}/10"
            )

            st.markdown(
                st.session_state.interview_feedback
            )

        # ----------------------------------------------------
        # NEW QUESTION
        # ----------------------------------------------------

        if st.button(
            "🔄 Generate Another Question"
        ):

            st.session_state.interview_question = ""

            st.session_state.interview_feedback = ""

            st.session_state.interview_score = 0

            st.session_state.voice_answer = ""

            st.rerun()

    st.divider()

    st.subheader(
        "🎤 Voice Interview Flow"
    )

    st.write(
        "1. Generate an AI question"
    )

    st.write(
        "2. Listen to the question"
    )

    st.write(
        "3. Record your answer"
    )

    st.write(
        "4. Speech is converted to text"
    )

    st.write(
        "5. AI evaluates your answer"
    )

    st.info(
        "Voice recognition uses your browser microphone "
        "and speech recognition. Internet access may be "
        "required for speech-to-text."
    )


# ============================================================
# RESUME ANALYZER
# ============================================================

elif page == "📄 Resume Analyzer":

    st.title(
        "📄 AI Resume Analyzer"
    )

    st.write(
        "Upload your resume and receive AI-powered feedback."
    )

    uploaded_file = st.file_uploader(
        "Upload Resume PDF",
        type=["pdf"]
    )

    if uploaded_file:

        st.success(
            "✅ Resume uploaded."
        )

        if st.button(
            "🔍 Analyze Resume"
        ):

            try:

                reader = PdfReader(
                    uploaded_file
                )

                text = ""

                for pdf_page in reader.pages:

                    page_text = pdf_page.extract_text()

                    if page_text:

                        text += (
                            page_text
                            + "\n"
                        )

                st.session_state.resume_text = (
                    text
                )

                if not text.strip():

                    st.warning(
                        "Could not extract text from this PDF."
                    )

                else:

                    st.subheader(
                        "📄 Resume Content"
                    )

                    st.text_area(
                        "Extracted Text",
                        text,
                        height=300
                    )

                    with st.spinner(
                        "🤖 AI is analyzing your resume..."
                    ):

                        prompt = f"""
You are an expert college placement resume reviewer.

Analyze this resume:

{text}

Provide:

1. Overall Resume Score out of 100
2. Skills identified
3. Technical strengths
4. Missing skills
5. Project quality
6. Resume formatting suggestions
7. Placement readiness
8. Specific improvements
9. Recommended skills for the student's target role

Keep the explanation simple and practical for a college student.
"""

                        st.session_state.resume_analysis = (
                            ask_ai(prompt)
                        )

            except Exception as e:

                st.error(
                    f"Resume analysis error: {e}"
                )

    if st.session_state.get(
        "resume_analysis"
    ):

        st.divider()

        st.subheader(
            "🤖 AI Resume Analysis"
        )

        st.markdown(
            st.session_state.resume_analysis
        )


# ============================================================
# DSA PRACTICE
# ============================================================

elif page == "🧠 DSA Practice":

    st.title(
        "🧠 Data Structures & Algorithms Practice"
    )

    st.write(
        "Practice common DSA questions asked in placements."
    )

    dsa_questions = [

        {
            "q": "Which data structure follows LIFO?",
            "options": [
                "Queue",
                "Stack",
                "Array",
                "Tree"
            ],
            "answer": "Stack"
        },

        {
            "q": "Which data structure follows FIFO?",
            "options": [
                "Stack",
                "Queue",
                "Tree",
                "Graph"
            ],
            "answer": "Queue"
        },

        {
            "q": (
                "What is the time complexity of binary search?"
            ),
            "options": [
                "O(n)",
                "O(n²)",
                "O(log n)",
                "O(1)"
            ],
            "answer": "O(log n)"
        },

        {
            "q": (
                "Which sorting algorithm has average "
                "O(n log n) complexity?"
            ),
            "options": [
                "Bubble Sort",
                "Selection Sort",
                "Merge Sort",
                "Linear Search"
            ],
            "answer": "Merge Sort"
        },

        {
            "q": (
                "Which structure is commonly used "
                "for hierarchical data?"
            ),
            "options": [
                "Stack",
                "Queue",
                "Tree",
                "Array"
            ],
            "answer": "Tree"
        }

    ]

    answers = []

    for i, question in enumerate(
        dsa_questions
    ):

        answer = st.radio(
            f"{i + 1}. {question['q']}",
            question["options"],
            key=f"dsa_{user_id}_{i}"
        )

        answers.append(
            answer
        )

    if st.button(
        "📝 Submit DSA Test"
    ):

        score = sum(
            answers[i]
            == dsa_questions[i]["answer"]
            for i in range(
                len(dsa_questions)
            )
        )

        save_score(
            user_id,
            "dsa",
            score
        )

        st.session_state.dsa_score = score

        st.session_state.dsa_completed = True

        st.success(
            f"Your DSA score is {score}/5"
        )

    if st.session_state.dsa_completed:

        if st.button(
            "🤖 Explain DSA Concepts"
        ):

            try:

                explanation = ask_ai(
                    """
Explain these DSA concepts to a beginner:

Stack,
Queue,
Binary Search,
Merge Sort
and Tree.

Give simple definitions and examples.
"""
                )

                st.markdown(
                    explanation
                )

            except Exception as e:

                st.error(
                    str(e)
                )


# ============================================================
# SQL PRACTICE
# ============================================================

elif page == "🗄️ SQL Practice":

    st.title(
        "🗄️ SQL Practice"
    )

    st.write(
        "Practice SQL concepts commonly asked in placements."
    )

    sql_questions = [

        {
            "q": (
                "Which command is used to retrieve data?"
            ),
            "options": [
                "INSERT",
                "SELECT",
                "DELETE",
                "UPDATE"
            ],
            "answer": "SELECT"
        },

        {
            "q": "Which clause filters rows?",
            "options": [
                "GROUP BY",
                "ORDER BY",
                "WHERE",
                "JOIN"
            ],
            "answer": "WHERE"
        },

        {
            "q": "Which function counts rows?",
            "options": [
                "SUM()",
                "AVG()",
                "COUNT()",
                "MAX()"
            ],
            "answer": "COUNT()"
        },

        {
            "q": "Which clause groups rows?",
            "options": [
                "GROUP BY",
                "ORDER BY",
                "WHERE",
                "FROM"
            ],
            "answer": "GROUP BY"
        },

        {
            "q": (
                "Which keyword removes duplicate results?"
            ),
            "options": [
                "UNIQUE",
                "DISTINCT",
                "REMOVE",
                "DELETE"
            ],
            "answer": "DISTINCT"
        }

    ]

    answers = []

    for i, question in enumerate(
        sql_questions
    ):

        answer = st.radio(
            f"{i + 1}. {question['q']}",
            question["options"],
            key=f"sql_{user_id}_{i}"
        )

        answers.append(
            answer
        )

    if st.button(
        "📝 Submit SQL Test"
    ):

        score = sum(
            answers[i]
            == sql_questions[i]["answer"]
            for i in range(
                len(sql_questions)
            )
        )

        save_score(
            user_id,
            "sql",
            score
        )

        st.session_state.sql_score = score

        st.session_state.sql_completed = True

        st.success(
            f"Your SQL score is {score}/5"
        )

    st.divider()

    st.subheader(
        "💻 SQL Query Practice"
    )

    sql_code = st.text_area(
        "Write a SQL query:",
        value=(
            "SELECT * FROM students "
            "WHERE marks > 80;"
        ),
        height=150
    )

    if st.button(
        "🤖 Explain SQL Query"
    ):

        try:

            explanation = ask_ai(
                f"""
Explain this SQL query to a beginner:

{sql_code}

Explain:

1. What it does
2. Each SQL keyword
3. Expected result
4. A similar example
"""
            )

            st.markdown(
                explanation
            )

        except Exception as e:

            st.error(
                str(e)
            )


# ============================================================
# AI PLACEMENT ASSISTANT
# ============================================================

elif page == "💬 AI Placement Assistant":

    st.title(
        "💬 AI Placement Assistant"
    )

    st.write(
        "Ask the AI anything about placement preparation."
    )

    st.info(
        "Examples: What should I learn for a Data Analyst job?"
    )

    user_question = st.text_area(
        "Ask your question:",
        height=150,
        placeholder=(
            "Example: How should I prepare "
            "for placements as a Data Science student?"
        )
    )

    if st.button(
        "🤖 Ask AI"
    ):

        if not user_question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            try:

                prompt = f"""
You are an AI college placement mentor.

Answer the student's question clearly.

Student Question:

{user_question}

The student is preparing for college placements.

Give:

- Direct answer
- Simple explanation
- Practical steps
- Examples where useful
- Beginner-friendly guidance
"""

                with st.spinner(
                    "🤖 AI is thinking..."
                ):

                    answer = ask_ai(
                        prompt
                    )

                st.subheader(
                    "🤖 AI Mentor"
                )

                st.markdown(
                    answer
                )

            except Exception as e:

                st.error(
                    "Could not connect to Ollama."
                )

                st.code(
                    str(e)
                )


# ============================================================
# PLACEMENT ROADMAP
# ============================================================

elif page == "🎯 Placement Roadmap":

    st.title(
        "🎯 Placement Preparation Roadmap"
    )

    st.write(
        "Complete these steps to become placement ready."
    )

    roadmap_items = [

        "Learn Python / Java fundamentals",

        "Learn Data Structures and Algorithms",

        "Learn SQL and DBMS",

        "Practice Aptitude",

        "Build Data Science / AI Projects",

        "Create a strong Resume",

        "Practice Technical and HR Interviews",

        "Practice Coding Problems",

        "Improve Communication Skills",

        "Apply for Internships and Placements"

    ]

    roadmap_data = get_roadmap(
        user_id,
        len(roadmap_items)
    )

    completed = 0

    for i, item in enumerate(
        roadmap_items
    ):

        checked = st.checkbox(
            item,
            value=roadmap_data.get(
                i,
                False
            ),
            key=f"roadmap_{user_id}_{i}"
        )

        save_roadmap_item(
            user_id,
            i,
            checked
        )

        if checked:

            completed += 1

    st.divider()

    progress = (
        completed
        /
        len(roadmap_items)
    )

    st.progress(
        progress
    )

    st.write(
        f"### {completed}/{len(roadmap_items)} completed"
    )

    if completed == len(
        roadmap_items
    ):

        st.success(
            "🎉 You completed the entire placement roadmap!"
        )


# ============================================================
# PROGRESS
# ============================================================

elif page == "📊 Progress":

    st.title(
        "📊 Placement Preparation Progress"
    )

    st.write(
        f"Personalized progress for "
        f"**{current_user['username']}**"
    )

    st.divider()

    scores = get_scores(
        user_id
    )

    st.session_state.aptitude_score = (
        scores["aptitude_score"]
    )

    st.session_state.dsa_score = (
        scores["dsa_score"]
    )

    st.session_state.sql_score = (
        scores["sql_score"]
    )

    interviews = get_interviews(
        user_id
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "📚 Aptitude",
            f"{scores['aptitude_score']}/5"
        )

    with col2:

        st.metric(
            "🧠 DSA",
            f"{scores['dsa_score']}/5"
        )

    with col3:

        st.metric(
            "🗄️ SQL",
            f"{scores['sql_score']}/5"
        )

    with col4:

        st.metric(
            "🤖 Interviews",
            len(interviews)
        )

    st.divider()

    st.subheader(
        "🤖 Interview History"
    )

    if interviews:

        for i, interview in enumerate(
            interviews,
            start=1
        ):

            (
                question,
                answer,
                score,
                interview_type,
                difficulty,
                created_at
            ) = interview

            with st.expander(
                f"Interview {i} — "
                f"{interview_type} — "
                f"Score {score}/10"
            ):

                st.write(
                    "**Question:**"
                )

                st.write(
                    question
                )

                st.write(
                    "**Your Answer:**"
                )

                st.write(
                    answer
                )

                st.write(
                    f"**Score:** {score}/10"
                )

                st.caption(
                    f"Difficulty: {difficulty} | "
                    f"Attempted: {created_at}"
                )

    else:

        st.info(
            "No interview attempts yet."
        )

    st.divider()

    st.subheader(
        "📈 Overall Preparation"
    )

    total_scores = (
        scores["aptitude_score"]
        +
        scores["dsa_score"]
        +
        scores["sql_score"]
    )

    max_scores = 15

    overall_progress = (
        total_scores
        /
        max_scores
    )

    st.progress(
        overall_progress
    )

    st.write(
        f"Current test performance: "
        f"{total_scores}/{max_scores}"
    )

    if overall_progress >= 0.8:

        st.success(
            "🌟 Excellent preparation progress!"
        )

    elif overall_progress >= 0.5:

        st.info(
            "👍 Good progress. Keep practicing!"
        )

    else:

        st.warning(
            "💪 Keep practicing to improve "
            "your placement readiness."
        )

    st.divider()

    st.subheader(
        "🚀 Recommended Next Steps"
    )

    if scores["aptitude_score"] < 3:

        st.write(
            "📚 Practice more aptitude questions."
        )

    if scores["dsa_score"] < 3:

        st.write(
            "🧠 Strengthen your DSA fundamentals."
        )

    if scores["sql_score"] < 3:

        st.write(
            "🗄️ Practice SQL queries and joins."
        )

    if len(interviews) == 0:

        st.write(
            "🤖 Attempt your first AI mock interview."
        )

    if (
        len(interviews) > 0
        and
        (
            sum(
                i[2]
                for i in interviews
            )
            /
            len(interviews)
        ) < 6
    ):

        st.write(
            "🎤 Practice speaking and improve "
            "your interview answers."
        )

    st.write(
        "💻 Try different random coding questions "
        "in Python, Java and C++."
    )

    st.success(
        "🎓 Keep learning, practicing and improving!"
    )