from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('question/<int:id>/', views.view_question, name='view_question'),
    path('ask/', views.ask_question, name='ask_question'),
    path('search/', views.search_questions, name='search_questions'),
    path('question/<int:pk>/edit/', views.edit_question, name='edit_question'),
    path('question/<int:pk>/delete/', views.delete_question, name='delete_question'),
    path('delete-file/<int:id>/', views.delete_question_file, name='delete_file'),
    path('comment/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path("profile/", views.profile, name="profile"),
    path("remove-dp/", views.remove_profile_pic, name="remove_profile_pic"),
    path("ai/suggest/<int:question_id>/", views.ai_suggest, name="ai_suggest"),
]
