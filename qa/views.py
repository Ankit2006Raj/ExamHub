from django.contrib import messages
from django.shortcuts import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from qa.models import Answer, Question, Test, TestSubmission
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone
from datetime import datetime
import pyttsx3 as pt


# speaking function
def speak(text):
    try:
        engine = pt.init()
        engine.say(text)
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.8)
        engine.setProperty('voice', 'english+f3')
        engine.runAndWait()
    except Exception:
        pass  # Don't crash if TTS fails


def calculate_score(test, user):
    """Calculate MCQ score for a user on a test."""
    score = 0
    for question in test.questions.filter(question_type='MCQ'):
        answer = Answer.objects.filter(question=question, user=user).first()
        if answer and answer.answer_text.upper() == (question.correct_answer or '').upper():
            score += question.marks
    return score

def home(request):
    now = timezone.now()
    available_tests = Test.objects.filter(is_active=True, start_time__lte=now, end_time__gte=now)
    upcoming_tests = Test.objects.filter(is_active=True, start_time__gt=now).order_by('start_time')
    expired_tests = Test.objects.filter(is_active=True, end_time__lt=now).order_by('-end_time')[:5]

    # Tests the logged-in user has already completed
    completed_test_ids = set()
    if request.user.is_authenticated:
        completed_test_ids = set(
            TestSubmission.objects.filter(user=request.user).values_list('test_id', flat=True)
        )

    context = {
        'available_tests': available_tests,
        'upcoming_tests': upcoming_tests,
        'expired_tests': expired_tests,
        'completed_test_ids': completed_test_ids,
        'now': now,
    }
    return render(request, 'home.html', context)

# View test questions
@login_required
def take_test(request, test_id):
    try:
        test = Test.objects.get(id=test_id)
    except Test.DoesNotExist:
        messages.error(request, "Test not found.")
        return redirect('home')

    # Check if test is available
    if not test.is_available():
        if test.is_upcoming():
            messages.error(request, f"Test '{test.name}' is not yet available. It starts at {test.start_time.strftime('%B %d, %Y %I:%M %p')}")
        elif test.is_expired():
            messages.error(request, f"Test '{test.name}' has expired.")
        return redirect('home')

    # Check if user already submitted
    if TestSubmission.objects.filter(test=test, user=request.user).exists():
        messages.info(request, f"You have already completed the '{test.name}' test.")
        return redirect('test_result', test_id=test.id)

    questions = test.questions.all().order_by('id')

    if request.method == "POST":
        # Handle final submit (manual or auto from timer)
        if request.POST.get("final_submit"):
            time_taken = int(request.POST.get("time_taken_seconds", 0))
            score = calculate_score(test, request.user)
            TestSubmission.objects.create(
                test=test,
                user=request.user,
                is_completed=True,
                score=score,
                time_taken_seconds=time_taken,
            )
            messages.success(request, f"Test '{test.name}' submitted successfully!")
            return redirect('test_result', test_id=test.id)

        # Handle answer save/update
        question_id = request.POST.get("question_id")
        answer_text = request.POST.get("answer", "").strip()
        try:
            question = Question.objects.get(id=question_id, test=test)
            existing_answer = Answer.objects.filter(question=question, user=request.user).first()
            if existing_answer:
                existing_answer.answer_text = answer_text
                existing_answer.save()
            else:
                if answer_text:
                    Answer.objects.create(question=question, user=request.user, answer_text=answer_text)
            return redirect('take_test', test_id=test.id)
        except Question.DoesNotExist:
            messages.error(request, "Question does not exist.")

    # Build answered set for template
    answered_ids = set(
        Answer.objects.filter(user=request.user, question__test=test).values_list('question_id', flat=True)
    )

    context = {
        'test': test,
        'questions': questions,
        'answered_ids': answered_ids,
        'answered_count': len(answered_ids),
    }
    return render(request, 'take_test.html', context)

# Test result page (replaces old test_completed)
@login_required
def test_result(request, test_id):
    try:
        test = Test.objects.get(id=test_id)
        submission = TestSubmission.objects.get(test=test, user=request.user)
    except (Test.DoesNotExist, TestSubmission.DoesNotExist):
        return redirect('home')

    questions = test.questions.all().order_by('id')
    # Build answer map for this user
    user_answers = {a.question_id: a for a in Answer.objects.filter(user=request.user, question__test=test)}

    question_results = []
    for q in questions:
        ans = user_answers.get(q.id)
        is_correct = None
        if q.question_type == 'MCQ' and ans:
            is_correct = ans.answer_text.upper() == (q.correct_answer or '').upper()
        question_results.append({
            'question': q,
            'answer': ans,
            'is_correct': is_correct,
        })

    total_marks = test.total_marks()
    mcq_questions = questions.filter(question_type='MCQ').count()

    context = {
        'test': test,
        'submission': submission,
        'question_results': question_results,
        'total_marks': total_marks,
        'mcq_questions': mcq_questions,
    }
    return render(request, 'test_result.html', context)


# Keep old URL working
@login_required
def test_completed(request, test_id):
    return redirect('test_result', test_id=test_id)


# Leaderboard for a test
def leaderboard(request, test_id):
    try:
        test = Test.objects.get(id=test_id)
    except Test.DoesNotExist:
        return redirect('home')

    submissions = TestSubmission.objects.filter(test=test, is_completed=True)\
        .select_related('user').order_by('-score', 'time_taken_seconds')

    # Add rank
    ranked = []
    for i, sub in enumerate(submissions, 1):
        ranked.append({'rank': i, 'submission': sub})

    user_rank = None
    if request.user.is_authenticated:
        for entry in ranked:
            if entry['submission'].user == request.user:
                user_rank = entry['rank']
                break

    context = {
        'test': test,
        'ranked': ranked,
        'user_rank': user_rank,
        'total_marks': test.total_marks(),
    }
    return render(request, 'leaderboard.html', context)


# Student profile / history
@login_required
def profile(request):
    submissions = TestSubmission.objects.filter(user=request.user, is_completed=True)\
        .select_related('test').order_by('-submitted_at')

    history = []
    for sub in submissions:
        total = sub.test.total_marks() if sub.test else 0
        history.append({
            'submission': sub,
            'total_marks': total,
            'percentage': sub.percentage(),
            'passed': sub.passed(),
        })

    context = {
        'history': history,
        'total_tests_taken': len(history),
        'avg_score': round(sum(h['percentage'] for h in history) / len(history), 1) if history else 0,
    }
    return render(request, 'profile.html', context)
       

def user_login(request):
    
    if request.method=="POST":
        form=AuthenticationForm(data=request.POST)
        if form.is_valid():
            user=form.get_user()
            login(request, user)
            return redirect('home')
    
    else:
        form=AuthenticationForm()
    speak("Welcome back! Please log in to access your tests and track your progress. If you don't have an account, feel free to register and start your learning journey with us!")
    return render(request, 'login.html', {'form': form})

# def register(request):
    
#     if request.method=="POST":
#         form=UserCreationForm(data=request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Registration successful. Please log in.")
#             return redirect('login')
#     else:
#         form=UserCreationForm()
#     return render(request, 'register.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('home')

def admin_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:  # Only allow admin/staff
                login(request, user)
                return redirect('admin_dashboard')  # Change to your admin dashboard URL name
            else:
                messages.error(request, "You are not authorized as admin.")
        else:
            messages.error(request, "Invalid credentials.")
    else:
        form = AuthenticationForm()
    return render(request, 'admin_login.html', {'form': form})

# Admin Dashboard View
@login_required
def admin_dashboard(request):
    # Only allow superuser or staff to access
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Handle adding new test
    if request.method == "POST" and 'create_test' in request.POST:
        name = request.POST.get('test_name')
        description = request.POST.get('test_description')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        duration_minutes = request.POST.get('duration_minutes')
        
        if name and description and start_time and end_time and duration_minutes:
            try:
                # Create the test with timezone-aware datetimes
                start_dt = timezone.make_aware(datetime.fromisoformat(start_time))
                end_dt = timezone.make_aware(datetime.fromisoformat(end_time))
                passing_marks = int(request.POST.get('passing_marks', 0) or 0)

                test = Test.objects.create(
                    name=name,
                    description=description,
                    start_time=start_dt,
                    end_time=end_dt,
                    duration_minutes=int(duration_minutes),
                    passing_marks=passing_marks,
                    created_by=request.user,
                    is_active=True
                )
                
                # Process questions if any
                questions_added = 0
                question_index = 1
                while True:
                    q_type = request.POST.get(f'questions[{question_index}][type]')
                    if not q_type:
                        break
                    
                    q_title = request.POST.get(f'questions[{question_index}][title]')
                    q_description = request.POST.get(f'questions[{question_index}][description]')
                    
                    if q_title and q_description:
                        q_marks = int(request.POST.get(f'questions[{question_index}][marks]', 1) or 1)
                        if q_type == 'MCQ':
                            option_a = request.POST.get(f'questions[{question_index}][option_a]')
                            option_b = request.POST.get(f'questions[{question_index}][option_b]')
                            option_c = request.POST.get(f'questions[{question_index}][option_c]')
                            option_d = request.POST.get(f'questions[{question_index}][option_d]')
                            correct_answer = request.POST.get(f'questions[{question_index}][correct_answer]')

                            if option_a and option_b and option_c and option_d and correct_answer:
                                Question.objects.create(
                                    test=test,
                                    title=q_title,
                                    description=q_description,
                                    question_type=q_type,
                                    option_a=option_a,
                                    option_b=option_b,
                                    option_c=option_c,
                                    option_d=option_d,
                                    correct_answer=correct_answer,
                                    marks=q_marks,
                                    user=request.user
                                )
                                questions_added += 1
                        else:
                            # Text question
                            Question.objects.create(
                                test=test,
                                title=q_title,
                                description=q_description,
                                question_type=q_type,
                                marks=q_marks,
                                user=request.user
                            )
                            questions_added += 1
                    
                    question_index += 1
                
                messages.success(request, f"Test created successfully with {questions_added} question(s)!")
                return redirect('admin_dashboard')
            except Exception as e:
                messages.error(request, f"Error creating test: {str(e)}")
        else:
            messages.error(request, "Please fill all test fields.")
    
    # Handle adding new question
    if request.method == "POST" and 'create_question' in request.POST:
        test_id = request.POST.get('test_id')
        title = request.POST.get('title')
        description = request.POST.get('description')
        question_type = request.POST.get('question_type')
        
        if title and description and question_type:
            test = None
            if test_id:
                try:
                    test = Test.objects.get(id=test_id)
                except Test.DoesNotExist:
                    messages.error(request, "Selected test not found.")
                    return redirect('admin_dashboard')

            marks = int(request.POST.get('marks', 1) or 1)

            if question_type == 'MCQ':
                option_a = request.POST.get('option_a')
                option_b = request.POST.get('option_b')
                option_c = request.POST.get('option_c')
                option_d = request.POST.get('option_d')
                correct_answer = request.POST.get('correct_answer')

                if option_a and option_b and option_c and option_d and correct_answer:
                    Question.objects.create(
                        test=test, title=title, description=description,
                        question_type=question_type, option_a=option_a, option_b=option_b,
                        option_c=option_c, option_d=option_d, correct_answer=correct_answer,
                        marks=marks, user=request.user
                    )
                    messages.success(request, "MCQ Question added successfully!")
                else:
                    messages.error(request, "Please fill all MCQ options and select correct answer.")
            else:
                Question.objects.create(
                    test=test, title=title, description=description,
                    question_type=question_type, marks=marks, user=request.user
                )
                messages.success(request, "Textual Question added successfully!")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please fill all required fields.")
    
    # Get statistics
    total_tests = Test.objects.filter(is_active=True).count()
    total_questions = Question.objects.count()
    total_answers = Answer.objects.count()
    total_users = User.objects.count()
    
    # Get all tests
    tests = Test.objects.all().order_by('-created_at')
    
    # Get all questions with their answers
    questions = Question.objects.all().order_by('-created_at')
    
    # Get all users with their activity
    users = User.objects.all().order_by('-date_joined')
    
    # Get students who completed the test
    completed_students = TestSubmission.objects.all().select_related('user', 'test').order_by('-submitted_at')
    
    context = {
        'total_tests': total_tests,
        'total_questions': total_questions,
        'total_answers': total_answers,
        'total_users': total_users,
        'tests': tests,
        'questions': questions,
        'users': users,
        'completed_students': completed_students,
    }
    return render(request, 'admin_dashboard.html', context)

# Delete Test (Admin only)
@login_required
def delete_test(request, test_id):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "You don't have permission to delete tests.")
        return redirect('home')
    
    try:
        test = Test.objects.get(id=test_id)
        test_name = test.name
        test.delete()
        messages.success(request, f"Test '{test_name}' deleted successfully!")
    except Test.DoesNotExist:
        messages.error(request, "Test not found.")
    
    return redirect('admin_dashboard')

# Delete Question (Admin only)
@login_required
def delete_question(request, question_id):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "You don't have permission to delete questions.")
        return redirect('home')
    
    try:
        question = Question.objects.get(id=question_id)
        question.delete()
        messages.success(request, "Question deleted successfully!")
    except Question.DoesNotExist:
        messages.error(request, "Question not found.")
    
    return redirect('admin_dashboard')

# Delete Answer (Admin only)
@login_required
def delete_answer(request, answer_id):
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "You don't have permission to delete answers.")
        return redirect('home')

    try:
        answer = Answer.objects.get(id=answer_id)
        answer.delete()
        messages.success(request, "Answer deleted successfully!")
    except Answer.DoesNotExist:
        messages.error(request, "Answer not found.")

    return redirect('admin_dashboard')


# Edit Test (Admin only)
@login_required
def edit_test(request, test_id):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('home')
    try:
        test = Test.objects.get(id=test_id)
    except Test.DoesNotExist:
        messages.error(request, "Test not found.")
        return redirect('admin_dashboard')

    if request.method == 'POST':
        test.name = request.POST.get('test_name', test.name)
        test.description = request.POST.get('test_description', test.description)
        test.duration_minutes = int(request.POST.get('duration_minutes', test.duration_minutes))
        test.passing_marks = int(request.POST.get('passing_marks', test.passing_marks))
        test.is_active = request.POST.get('is_active') == 'on'
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        if start_time:
            test.start_time = timezone.make_aware(datetime.fromisoformat(start_time))
        if end_time:
            test.end_time = timezone.make_aware(datetime.fromisoformat(end_time))
        test.save()
        messages.success(request, f"Test '{test.name}' updated successfully!")
        return redirect('admin_dashboard')

    context = {'test': test}
    return render(request, 'edit_test.html', context)


# Edit Question (Admin only)
@login_required
def edit_question(request, question_id):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('home')
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        messages.error(request, "Question not found.")
        return redirect('admin_dashboard')

    if request.method == 'POST':
        question.title = request.POST.get('title', question.title)
        question.description = request.POST.get('description', question.description)
        question.marks = int(request.POST.get('marks', question.marks))
        if question.question_type == 'MCQ':
            question.option_a = request.POST.get('option_a', question.option_a)
            question.option_b = request.POST.get('option_b', question.option_b)
            question.option_c = request.POST.get('option_c', question.option_c)
            question.option_d = request.POST.get('option_d', question.option_d)
            question.correct_answer = request.POST.get('correct_answer', question.correct_answer)
        question.save()
        messages.success(request, "Question updated successfully!")
        return redirect('admin_dashboard')

    context = {'question': question}
    return render(request, 'edit_question.html', context)
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        form.fields['username'].widget.attrs['placeholder'] = 'Enter admin username'
        form.fields['password'].widget.attrs['placeholder'] = 'Enter admin password'
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser or user.is_staff:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('admin_dashboard')
            else:
                messages.error(request, "⚠️ You don't have admin privileges!")
        else:
            messages.error(request, "❌ Invalid username or password!")
    else:
        form = AuthenticationForm()
        form.fields['username'].widget.attrs['placeholder'] = 'Enter admin username'
        form.fields['password'].widget.attrs['placeholder'] = 'Enter admin password'
    return render(request, 'admin_login.html', {'form': form})

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# ...existing imports...

def register(request):
    """User registration with email confirmation"""
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Validation
        if password1 != password2:
            messages.error(request, '❌ Passwords do not match!')
            return render(request, 'register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Username already exists!')
            return render(request, 'register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, '❌ Email already registered!')
            return render(request, 'register.html')
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            
            # ✅ SEND WELCOME EMAIL
            send_welcome_email(user)

            # Log the user in
            login(request, user)

            # Speak only after successful registration
            speak("Welcome to the Q&A Platform! Your registration was successful. Check your email for a welcome message and start exploring our tests and features. Happy learning!")

            messages.success(request, f'🎉 Welcome {username}! Your account has been created successfully. Check your email for confirmation.')
            return redirect('home')  # Redirect to home page

        except Exception as e:
            messages.error(request, f'❌ Error creating account: {str(e)}')
    return render(request, 'register.html')


def send_welcome_email(user):
    """
    Send welcome/confirmation email to newly registered user
    """
    subject = f'🎉 Welcome to Q&A Platform, {user.first_name or user.username}!'
    
    # HTML Email Content
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                background: #f5f7fa;
                margin: 0;
                padding: 0;
            }}
            .email-wrapper {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 32px;
            }}
            .header-icon {{
                font-size: 60px;
                margin-bottom: 10px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .welcome-box {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                padding: 30px;
                border-radius: 12px;
                text-align: center;
                margin: 20px 0;
            }}
            .welcome-box h2 {{
                margin: 0 0 10px 0;
                font-size: 28px;
            }}
            .info-box {{
                background: #f0f4ff;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                border-left: 4px solid #667eea;
            }}
            .info-row {{
                padding: 10px 0;
                border-bottom: 1px solid #e0e0e0;
            }}
            .info-row:last-child {{
                border-bottom: none;
            }}
            .info-label {{
                font-weight: bold;
                color: #667eea;
                display: inline-block;
                min-width: 120px;
            }}
            .features {{
                margin: 30px 0;
            }}
            .feature-item {{
                display: flex;
                align-items: flex-start;
                gap: 15px;
                margin: 15px 0;
                padding: 15px;
                background: #f8fafc;
                border-radius: 8px;
            }}
            .feature-icon {{
                font-size: 28px;
                flex-shrink: 0;
            }}
            .feature-text h3 {{
                margin: 0 0 5px 0;
                color: #2d3748;
                font-size: 18px;
            }}
            .feature-text p {{
                margin: 0;
                color: #718096;
                font-size: 14px;
            }}
            .cta-button {{
                display: inline-block;
                padding: 15px 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
                margin: 20px 0;
            }}
            .cta-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .footer {{
                background: #f8fafc;
                padding: 30px;
                text-align: center;
                color: #718096;
                font-size: 13px;
            }}
            .footer a {{
                color: #667eea;
                text-decoration: none;
            }}
            .social-links {{
                margin: 20px 0;
            }}
            .social-links a {{
                display: inline-block;
                margin: 0 10px;
                font-size: 24px;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="header">
                <div class="header-icon">🎓</div>
                <h1>Q&A Platform</h1>
            </div>
            
            <div class="content">
                <div class="welcome-box">
                    <h2>🎉 Welcome Aboard!</h2>
                    <p style="margin: 0; font-size: 18px;">Your learning journey starts here</p>
                </div>
                
                <p>Hi <strong>{user.first_name or user.username}</strong>,</p>
                
                <p>Thank you for joining <strong>Q&A Platform</strong>! We're excited to have you as part of our learning community.</p>
                
                <div class="info-box">
                    <div class="info-row">
                        <span class="info-label">👤 Username:</span>
                        <span>{user.username}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">📧 Email:</span>
                        <span>{user.email}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">📅 Joined:</span>
                        <span>{user.date_joined.strftime('%B %d, %Y at %I:%M %p')}</span>
                    </div>
                </div>
                
                <h2 style="color: #2d3748; margin-top: 30px;">🚀 What You Can Do:</h2>
                
                <div class="features">
                    <div class="feature-item">
                        <div class="feature-icon">📝</div>
                        <div class="feature-text">
                            <h3>Take Tests</h3>
                            <p>Access various tests and challenge yourself with MCQs and text-based questions</p>
                        </div>
                    </div>
                    
                    <div class="feature-item">
                        <div class="feature-icon">📊</div>
                        <div class="feature-text">
                            <h3>Track Progress</h3>
                            <p>Monitor your performance and see detailed results of all your attempts</p>
                        </div>
                    </div>
                    
                    <div class="feature-item">
                        <div class="feature-icon">🎯</div>
                        <div class="feature-text">
                            <h3>Instant Results</h3>
                            <p>Get immediate feedback on your answers and learn from your mistakes</p>
                        </div>
                    </div>
                    
                    <div class="feature-item">
                        <div class="feature-icon">🔔</div>
                        <div class="feature-text">
                            <h3>Email Notifications</h3>
                            <p>Receive updates whenever new tests are uploaded to the platform</p>
                        </div>
                    </div>
                </div>
                
                <div class="cta-container">
                    <a href="http://127.0.0.1:8000/" class="cta-button">🎓 Start Learning Now</a>
                </div>
                
                <p style="margin-top: 30px; color: #718096; font-size: 14px;">
                    <strong>💡 Pro Tip:</strong> Make sure to check your email regularly for notifications about new tests and important updates!
                </p>
            </div>
            
            <div class="footer">
                <p><strong>Need Help?</strong></p>
                <p>If you have any questions or need assistance, feel free to contact our support team.</p>
                
                <div class="social-links">
                    <a href="#" title="Facebook">📘</a>
                    <a href="#" title="Twitter">🐦</a>
                    <a href="#" title="LinkedIn">💼</a>
                    <a href="#" title="Instagram">📷</a>
                </div>
                
                <p style="margin-top: 20px;">
                    © 2026 Q&A Platform. All rights reserved.<br>
                    This email was sent to <a href="mailto:{user.email}">{user.email}</a>
                </p>
                
                <p style="font-size: 11px; color: #a0aec0; margin-top: 20px;">
                    You received this email because you registered for an account on Q&A Platform.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version (fallback)
    plain_message = f"""
    Welcome to Q&A Platform!
    
    Hi {user.first_name or user.username},
    
    Thank you for joining Q&A Platform! We're excited to have you as part of our learning community.
    
    Your Account Details:
    - Username: {user.username}
    - Email: {user.email}
    - Joined: {user.date_joined.strftime('%B %d, %Y at %I:%M %p')}
    
    What You Can Do:
    ✓ Take Tests - Access various tests with MCQs and text-based questions
    ✓ Track Progress - Monitor your performance and results
    ✓ Instant Results - Get immediate feedback on your answers
    ✓ Email Notifications - Receive updates about new tests
    
    Start Learning: http://127.0.0.1:8000/
    
    Need help? Contact our support team anytime.
    
    © 2026 Q&A Platform. All rights reserved.
    """
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=html_message
        )
        print(f"✅ Welcome email sent to {user.email}")
        return True
    except Exception as e:
        print(f"❌ Error sending welcome email: {e}")
        return False