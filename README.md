# 🎓 AI-Powered College Placement Preparation Platform

An **AI-powered placement preparation platform** designed to help college students prepare for technical and placement interviews in one place.

The platform provides aptitude practice, coding practice, DSA and SQL practice, AI mock interviews, resume analysis, an AI placement assistant, a placement roadmap, and progress tracking.

---

## 🚀 Features

### 🏠 Dashboard

Provides an overview of the student's placement preparation progress and available modules.

### 👤 Student Profile

Students can enter and save their basic profile information, including branch, year, skills, and other details.

### 📚 Aptitude Practice

* Practice aptitude questions
* Submit answers
* Get scores
* Retake the test

### 💻 Coding Practice

Supports coding practice in:

* Python
* Java
* C++

Students can write code and execute it directly through the platform.

### 🤖 AI Mock Interview

The AI conducts mock interviews based on the selected category:

* Technical Interview
* HR Interview
* Mixed Interview

The AI generates interview questions and evaluates the student's answers.

The evaluation provides:

* Score out of 10
* Strengths
* Weaknesses
* Feedback
* Improved Answer

### 📄 Resume Analyzer

Students can upload their resume in PDF format.

The AI analyzes the resume and provides:

* Resume Score
* Skills identified
* Skill gaps
* Project quality feedback
* Formatting feedback
* Placement readiness
* Improvement suggestions

### 🧠 DSA Practice

Provides Data Structures and Algorithms practice questions with automatic scoring.

### 🗄️ SQL Practice

Provides SQL practice questions and evaluates student answers.

### 💬 AI Placement Assistant

An AI-based assistant that answers students' placement-related questions and provides preparation guidance.

### 🎯 Placement Roadmap

Provides a step-by-step placement preparation roadmap with progress tracking.

### 📊 Progress Tracking

Tracks the student's performance in:

* Aptitude
* DSA
* SQL
* AI Mock Interviews
* Placement Roadmap

---

## 🛠️ Technologies Used

| Technology            | Purpose                               |
| --------------------- | ------------------------------------- |
| Python                | Main programming language             |
| Streamlit             | Web application development           |
| Ollama                | Local AI model integration            |
| Llama 3.2             | AI question generation and evaluation |
| PyPDF                 | Resume PDF text extraction            |
| Sentence Transformers | AI/semantic processing                |
| ChromaDB              | Vector database support               |
| HTML/CSS              | Interface styling                     |

---

## 🤖 AI Integration

The platform uses **Ollama with the Llama 3.2 model** to provide local AI functionality.

AI is used for:

* Mock interview question generation
* Interview answer evaluation
* Resume analysis
* Placement-related assistance
* Personalized preparation guidance

Because Ollama runs locally, the application can use an AI model without requiring a cloud AI API key.

---

## 🏗️ System Architecture

```text
                STUDENT
                   │
                   ▼
        ┌─────────────────────┐
        │   Streamlit UI      │
        │  Presentation Layer │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Application Logic   │
        │                     │
        │ Aptitude            │
        │ Coding              │
        │ DSA / SQL           │
        │ Resume Analyzer     │
        │ Mock Interview      │
        │ Roadmap / Progress  │
        └──────────┬──────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
   ┌──────────────┐  ┌──────────────┐
   │ Ollama       │  │ PDF / Python │
   │ Llama 3.2    │  │ Processing   │
   └──────────────┘  └──────────────┘
          │
          ▼
       AI Results
```

---

## 📂 Project Structure

```text
capstone_project/
│
├── main.py
├── README.md
├── requirements.txt
├── .gitignore
└── venv/
```

> `venv/` should not be uploaded to GitHub. It is excluded using `.gitignore`.

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

### 2. Open the project folder

```bash
cd capstone_project
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows Git Bash:**

```bash
source venv/Scripts/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🦙 Install and Run Ollama

Make sure Ollama is installed and available on your system.

Check the installation:

```bash
ollama --version
```

Download the Llama 3.2 model:

```bash
ollama pull llama3.2
```

Run the model:

```bash
ollama run llama3.2
```

---

## ▶️ Run the Application

After activating the virtual environment:

```bash
python -m streamlit run main.py
```

The application will open in your browser at:

```text
http://localhost:8501
```

---

## 📦 Requirements

The main dependencies are:

```text
streamlit
sentence-transformers
chromadb
pypdf
ollama
```

Install them using:

```bash
pip install -r requirements.txt
```

---

## 🎯 Objective

The main objective of this project is to provide a **single platform for college students to prepare for placements** by combining traditional preparation methods with artificial intelligence.

Instead of using separate platforms for aptitude, coding, interviews, and resume preparation, students can access these features from one application.

---

## 🌟 Advantages

* All-in-one placement preparation platform
* AI-powered mock interviews
* Automated resume analysis
* Coding practice
* Aptitude, DSA, and SQL practice
* Placement roadmap
* Progress monitoring
* Local AI processing using Ollama
* Beginner-friendly interface

---

## 🔮 Future Enhancements

The platform can be further improved by adding:

* More aptitude, DSA, and SQL question banks
* AI-generated questions with different difficulty levels
* User authentication
* Database-based student accounts
* Leaderboards
* Personalized learning recommendations
* Company-specific interview preparation
* Job and internship recommendations
* Advanced resume scoring
* Performance analytics and visualizations

---

## 👩‍💻 Developed By

**D. Preethi**

B.Tech – Data Science

---

## 📌 Project Status

**Status: Completed and Functionally Tested ✅**

The major modules of the platform have been implemented and tested successfully.

---

## 📄 License

This project is developed for **educational and academic purposes**.
