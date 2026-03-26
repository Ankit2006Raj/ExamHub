# ExamHub — Online Q&A Exam Platform

A Django-based online examination platform where admins can create timed tests with MCQ and descriptive questions, and students can register, take tests, and submit answers.

## Features

- Student registration & login
- Admin dashboard to create/manage tests and questions
- Timed MCQ and descriptive question support
- Live, upcoming, and expired test tracking
- Test submission with completion confirmation
- Responsive UI built with Tailwind CSS + Alpine.js

## Tech Stack

- Python 3.12 / Django 6
- SQLite (default DB)
- Tailwind CSS (CDN)
- Alpine.js (CDN)

## Getting Started

```bash
# Clone the repo
git clone https://github.com/Ankit2006Raj/QnA-Exam-Platform.git
cd QnA-Exam-Platform

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

## Project Structure

```
QnA_Project/       # Django project settings
qa/                # Main app (models, views, templates, urls)
  templates/       # HTML templates
  migrations/      # DB migrations
manage.py
```

## Contact

Developed by **Ankit Raj**

- GitHub: [github.com/Ankit2006Raj](https://github.com/Ankit2006Raj)
- LinkedIn: [linkedin.com/in/ankit-raj-226a36309](https://www.linkedin.com/in/ankit-raj-226a36309)
- Email: ankit9905163014@gmail.com

---

© 2026 ExamHub. All rights reserved.
