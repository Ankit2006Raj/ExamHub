from django.db import models
from django.utils import timezone

class Test(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.IntegerField(help_text="Test duration in minutes")
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    passing_marks = models.IntegerField(default=0, help_text="Minimum marks to pass (0 = no pass/fail)")

    def __str__(self):
        return self.name

    def is_available(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    def is_upcoming(self):
        return self.is_active and timezone.now() < self.start_time

    def is_expired(self):
        return timezone.now() > self.end_time

    def total_marks(self):
        return self.questions.aggregate(total=models.Sum('marks'))['total'] or 0


class Question(models.Model):
    QUESTION_TYPES = (
        ('TEXT', 'Textual'),
        ('MCQ', 'Multiple Choice'),
    )

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='TEXT')
    option_a = models.CharField(max_length=200, blank=True, null=True)
    option_b = models.CharField(max_length=200, blank=True, null=True)
    option_c = models.CharField(max_length=200, blank=True, null=True)
    option_d = models.CharField(max_length=200, blank=True, null=True)
    correct_answer = models.CharField(max_length=1, blank=True, null=True)  # A, B, C, or D
    marks = models.IntegerField(default=1, help_text="Marks for this question")
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    answer_text = models.TextField()  # For TEXT questions or stores 'A', 'B', 'C', 'D' for MCQ
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Answer to: {self.question.title}'

    def is_correct(self):
        """Returns True if MCQ answer is correct, None for text questions."""
        if self.question.question_type == 'MCQ':
            return self.answer_text.upper() == (self.question.correct_answer or '').upper()
        return None


class TestSubmission(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='submissions', null=True, blank=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='test_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=True)
    score = models.IntegerField(default=0, help_text="Auto-calculated score for MCQ questions")
    time_taken_seconds = models.IntegerField(default=0, help_text="Time taken to complete the test in seconds")

    class Meta:
        unique_together = ('test', 'user')

    def __str__(self):
        return f'{self.user.username} - {self.test.name if self.test else "General"} Test Submitted'

    def percentage(self):
        total = self.test.total_marks() if self.test else 0
        if total == 0:
            return 0
        return round((self.score / total) * 100, 1)

    def passed(self):
        if self.test and self.test.passing_marks > 0:
            return self.score >= self.test.passing_marks
        return None  # No pass/fail threshold set