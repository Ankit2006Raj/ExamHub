from django.db import models
from django.utils import timezone

# Create your models here.
class Test(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.IntegerField(help_text="Test duration in minutes")
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def is_available(self):
        """Check if test is currently available"""
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time
    
    def is_upcoming(self):
        """Check if test is upcoming"""
        return self.is_active and timezone.now() < self.start_time
    
    def is_expired(self):
        """Check if test has expired"""
        return timezone.now() > self.end_time

class Question(models.Model):
    QUESTION_TYPES = (
        ('TEXT', 'Textual'),
        ('MCQ', 'Multiple Choice'),
    )
    
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='TEXT')
    # MCQ options (stored as JSON or separate fields)
    option_a = models.CharField(max_length=200, blank=True, null=True)
    option_b = models.CharField(max_length=200, blank=True, null=True)
    option_c = models.CharField(max_length=200, blank=True, null=True)
    option_d = models.CharField(max_length=200, blank=True, null=True)
    correct_answer = models.CharField(max_length=1, blank=True, null=True)  # A, B, C, or D
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

class TestSubmission(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='submissions', null=True, blank=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='test_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('test', 'user')
    
    def __str__(self):
        return f'{self.user.username} - {self.test.name if self.test else "General"} Test Submitted'