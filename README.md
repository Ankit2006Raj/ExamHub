# 🎓 ExamHub — Online Q&A Exam Platform

A Django-based online examination platform where admins can create timed tests with MCQ and descriptive questions, and students can register, take tests, and submit answers.

---

## ✨ Features

- Student registration & login
- Admin dashboard to create/manage tests and questions
- Timed MCQ and descriptive question support
- Live, upcoming, and expired test tracking
- Test submission with completion confirmation
- Responsive UI built with Tailwind CSS + Alpine.js

---

## 🛠 Tech Stack

| Layer      | Technology                  |
|------------|-----------------------------|
| Backend    | Python 3.12 / Django 6      |
| Database   | SQLite (default)            |
| Frontend   | Tailwind CSS (CDN)          |
| JS         | Alpine.js (CDN)             |

---

## 🚀 Getting Started

```bash
# Clone the repo
git clone https://github.com/Ankit2006Raj/ExamHub.git
cd ExamHub

# Install dependencies
pip install django

# Apply migrations
python manage.py migrate

# Create a superuser (admin)
python manage.py createsuperuser

# Run the server
python manage.py runserver
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## 📁 Project Structure

```
ExamHub/
├── QnA_Project/       # Django project settings
├── qa/                # Main app
│   ├── templates/     # HTML templates
│   ├── migrations/    # DB migrations
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── manage.py
├── db.sqlite3
└── README.md
```

---

## 📬 Contact

Developed by **Ankit Raj**

[![GitHub](https://img.shields.io/badge/GitHub-Ankit2006Raj-181717?logo=github)](https://github.com/Ankit2006Raj)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ankit%20Raj-0A66C2?logo=linkedin)](https://www.linkedin.com/in/ankit-raj-226a36309)
[![Email](https://img.shields.io/badge/Email-ankit9905163014%40gmail.com-D14836?logo=gmail)](mailto:ankit9905163014@gmail.com)

---

© 2026 ExamHub. All right reserved.
