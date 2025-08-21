from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Q
from django.http import HttpResponseForbidden
import random

from .models import OTP, CustomUser, Question, Comment, QuestionFile
from .forms import SignupForm, OTPForm, QuestionForm, CommentForm


# Home Page - Show recent questions
def home(request):
    questions = Question.objects.order_by('-created_at')[:10]
    return render(request, 'home.html', {'questions': questions})


# Signup View (Manual, not using SignupForm)
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            return render(request, 'signup.html', {'error': "Passwords do not match."})

        if CustomUser.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': "Email already exists."})

        if CustomUser.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': "Username already taken."})

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            password=password1
        )
        user.is_active = False
        user.save()

        otp_code = str(random.randint(100000, 999999))
        OTP.objects.create(user=user, code=otp_code)

        send_mail(
            'Your OTP Code',
            f'Your OTP is {otp_code}',
            'yourgmail@gmail.com',
            [email],
            fail_silently=False,
        )

        request.session['user_id'] = user.id
        return redirect('verify_otp')

    return render(request, 'signup.html')


# OTP Verification View
def verify_otp(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('signup')

    user = CustomUser.objects.get(id=user_id)
    otp_instance = OTP.objects.filter(user=user).last()

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if otp_instance.code == entered_otp and not otp_instance.is_expired():
            user.is_active = True
            user.save()
            login(request, user)
            messages.success(request, "Signup successful!")
            return redirect('home')
        else:
            messages.error(request, "Invalid or expired OTP.")

    return render(request, 'verify_otp.html')


# Resend OTP
def resend_otp(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('signup')

    user = CustomUser.objects.get(id=user_id)
    otp_code = str(random.randint(100000, 999999))
    OTP.objects.create(user=user, code=otp_code)

    send_mail(
        'Your OTP Code',
        f'Your new OTP is {otp_code}',
        'yourgmail@gmail.com',
        [user.email],
        fail_silently=False,
    )

    messages.success(request, "OTP has been resent.")
    return redirect('verify_otp')


# Login View
def login_view(request):
    if request.method == 'POST':
        uname = request.POST['username']
        pwd = request.POST['password']
        user = authenticate(request, username=uname, password=pwd)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials')

    return render(request, 'login.html')


# Logout View
def logout_view(request):
    logout(request)
    return redirect('home')


# Ask a Question (Login Required)
@login_required
def ask_question(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            question.user = request.user  # old model field
            question.author = request.user  # new model field
            question.save()
            return redirect('home')
    else:
        form = QuestionForm()
    return render(request, 'ask_question.html', {'form': form})


# View a single question with comments
def view_question(request, id):
    question = get_object_or_404(Question, id=id)
    comments = Comment.objects.filter(question=question).order_by('-created_at')
    if request.method == 'POST':
        if request.user.is_authenticated:
            form = CommentForm(request.POST, request.FILES)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.question = question
                comment.author = request.user
                comment.save()
                return redirect('view_question', id=id)
        else:
            return redirect('login')
    else:
        form = CommentForm()
    return render(request, 'view_question.html', {
        'question': question,
        'comments': comments,
        'form': form
    })


# Search Questions
def search_questions(request):
    query = request.GET.get('q')
    results = []
    if query:
        results = Question.objects.filter(
            Q(title__icontains=query) | Q(body__icontains=query)
        )
    return render(request, 'search_results.html', {'results': results, 'query': query})


# Question Delete View me security logic
@login_required
def delete_question_file(request, id):
    file = get_object_or_404(QuestionFile, id=id)
    if request.user == file.uploaded_by or request.user.is_superuser:
        if file.file:
            file.file.delete(save=False)
        file.delete()
        return redirect('home')
    else:
        return HttpResponseForbidden("You are not allowed to delete this file.")


# Delete Question
@login_required
def delete_question(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.user == question.user or request.user.is_superuser:
        question.delete()
        messages.success(request, "Post deleted successfully!")
        return redirect('home')
    else:
        messages.error(request, "You don't have permission to delete this post.")
        return redirect('view_question', pk=pk)


# Delete User (Admin Only)
@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    from django.contrib.auth.models import User
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, "User deleted successfully!")
    return redirect('home')


# Final merged edit_question view with file replace
@login_required
def edit_question(request, pk):
    question = get_object_or_404(Question, pk=pk)

    # Permission check
    if request.user != question.user and not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit this post.")
        return redirect('view_question', pk=pk)

    if request.method == 'POST':
        question.title = request.POST.get('title')
        question.description = request.POST.get('description')

        # File replace logic
        if 'file' in request.FILES and request.FILES['file']:
            if question.file:
                question.file.delete(save=False)  # delete old file
            question.file = request.FILES['file']  # set new file

        question.save()
        messages.success(request, "Post updated successfully!")
        return redirect('view_question', pk=question.pk)

    return render(request, 'edit_question.html', {'question': question})




# add files in comment , edit comment or del comment 

from django.shortcuts import render, get_object_or_404, redirect
from .models import Question, Comment
from .forms import CommentForm
from django.contrib.auth.decorators import login_required

@login_required
def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk)
    comments = question.comments.all()
    
    if request.method == "POST":
        form = CommentForm(request.POST, request.FILES)  # request.FILES added
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.question = question
            comment.save()
            return redirect('question_detail', pk=pk)
    else:
        form = CommentForm()

    return render(request, 'question_detail.html', {
        'question': question,
        'comments': comments,
        'form': form
    })

# Edit Comment
@login_required
# def edit_comment(request, comment_id):
#     comment = get_object_or_404(Comment, id=comment_id)

#     # Only author or superuser can edit
#     if request.user != comment.author and not request.user.is_superuser:
#         return redirect('question_detail', pk=comment.question.id)

#     if request.method == "POST":
#         form = CommentForm(request.POST, request.FILES, instance=comment)
#         if form.is_valid():
#             form.save()
#             return redirect('question_detail', pk=comment.question.id)
#     else:
#         form = CommentForm(instance=comment)

#     return render(request, 'edit_comment.html', {'form': form})


def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    # sirf apna comment ya superuser edit kar sake
    if request.user != comment.author and not request.user.is_superuser:
        return redirect('question_detail', question_id=comment.question.id)

    if request.method == "POST":
        form = CommentForm(request.POST, request.FILES, instance=comment) 
        if form.is_valid():
            form.save()
            return redirect('question_detail', pk=comment.question.id)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'edit_comment.html', {'form': form, 'comment': comment})


# Delete Comment
@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    # Only author or superuser can delete
    if request.user != comment.author and not request.user.is_superuser:
        return redirect('question_detail', pk=comment.question.id)

    question_id = comment.question.id
    comment.delete()
    return redirect('question_detail', pk=question_id)




# Profile FUnction 


from .models import Profile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm
@login_required
def profile(request):
    # Profile object create karo agar exist nahi karta
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profile updated successfully!")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'profile.html', {
        'form': form,
        'profile': profile
    })


# Remove Profile Picture
@login_required
def remove_profile_pic(request):
    if request.method == "POST":
        profile = request.user.profile
        profile.profile_picture.delete(save=False)  
        profile.profile_picture = None  
        profile.save()
    return redirect("profile")





# AI Suggestion View
# main/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from .models import Question  # apne model ka sahi naam use karein

@require_http_methods(["GET", "POST"])
def ai_suggest(request, question_id):
    """
    Always returns JsonResponse.
    Never falls through without return.
    """
    try:
        question = get_object_or_404(Question, pk=question_id)

        # Input text: POST 'text' > GET 'text' > question ka title/body
        text = (
            request.POST.get("text")
            or request.GET.get("text")
            or f"{getattr(question, 'title', '')}\n{getattr(question, 'body', '')}"
        ).strip()

        # Dummy suggestion (yaha apna AI/LLM/logic call karo)
        suggestions = generate_suggestions(text)

        return JsonResponse(
            {
                "ok": True,
                "question_id": question_id,
                "count": len(suggestions),
                "suggestions": suggestions,
            },
            status=200,
        )

    except Exception as e:
        # IMPORTANT: kabhi bhi None return mat hone do
        # yaha logging bhi kar sakte ho
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


def generate_suggestions(text: str):
    """
    Placeholder: apna AI logic yaha lagao.
    Return hamesha list/dict jaisa JSON-serializable hona chahiye.
    """
    base = text[:80].replace("\n", " ")
    return [
        f"Clarify the problem scope related to: '{base}...'",
        "Share sample input/output so helpers can reproduce.",
        "Add relevant tags and environment details (OS, versions).",
    ]




# from time import time

# @login_required
# @require_GET
# def ai_suggest(request, pk: int):
#     last = request.session.get("ai_last_ts", 0)
#     now = time()
#     if now - last < 8:  # 8 seconds cooldown
#         return JsonResponse({"ok": False, "error": "Slow down. Try again in a few seconds."}, status=429)
#     request.session["ai_last_ts"] = now
#     # ...baaki code same (as above) ...
