from django.contrib import admin

from qa.models import Answer, Question, Test, TestSubmission

# Register your models here.
admin.site.register(Test)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(TestSubmission)