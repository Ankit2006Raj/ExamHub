from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('test/<int:test_id>/', views.take_test, name='take_test'),
    path('test/<int:test_id>/completed/', views.test_completed, name='test_completed'),
    path('delete-test/<int:test_id>/', views.delete_test, name='delete_test'),
    path('delete-question/<int:question_id>/', views.delete_question, name='delete_question'),
    path('delete-answer/<int:answer_id>/', views.delete_answer, name='delete_answer'),
]
