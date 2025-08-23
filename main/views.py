from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_http_methods
import random

from .models import OTP, CustomUser, Question, Comment, Profile
from .forms import SignupForm, OTPForm, QuestionForm, CommentForm, ProfileUpdateForm


# Home Page
def home(request):
    questions = Question.objects.order_by('-created_at')[:10]
    return render(request, 'home.html', {'questions': questions})


# Signup View
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


# OTP Verification
def verify_otp(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('signup')

    user = CustomUser.objects.get(id=user_id)
    otp_instance = OTP.objects.filter(user=user).last()

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if otp_instance and otp_instance.code == entered_otp and not otp_instance.is_expired():
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


# Login
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


# Logout
def logout_view(request):
    logout(request)
    return redirect('home')


# Ask Question
@login_required
def ask_question(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            question.user = request.user
            question.author = request.user
            question.save()
            return redirect('home')
    else:
        form = QuestionForm()
    return render(request, 'ask_question.html', {'form': form})


# View Question + Comments
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


# Delete Question File
@login_required
def delete_question_file(request, id):
    file = get_object_or_404(QuestionFile, id=id)
    if request.user == file.uploaded_by or request.user.is_superuser:
        if file.file:
            file.file.delete(save=False)
        file.delete()
        messages.success(request, "File deleted successfully!")
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
        return redirect('view_question', id=pk)


# Delete User (Admin only)
@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    from django.contrib.auth.models import User
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, "User deleted successfully!")
    return redirect('home')


# Edit Question
@login_required
def edit_question(request, pk):
    question = get_object_or_404(Question, pk=pk)

    if request.user != question.user and not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit this post.")
        return redirect('view_question', id=question.pk)

    if request.method == 'POST':
        question.title = request.POST.get('title')
        question.body = request.POST.get('description')

        if 'file' in request.FILES and request.FILES['file']:
            if question.file:
                question.file.delete(save=False)
            question.file = request.FILES['file']

        question.save()
        messages.success(request, "Post updated successfully!")
        return redirect('view_question', id=question.pk)

    return render(request, 'edit_question.html', {'question': question})


# Edit Comment
@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if request.user != comment.author and not request.user.is_superuser:
        return redirect('view_question', id=comment.question.id)

    if request.method == "POST":
        form = CommentForm(request.POST, request.FILES, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('view_question', id=comment.question.id)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'edit_comment.html', {'form': form, 'comment': comment})


# Delete Comment
@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if request.user != comment.author and not request.user.is_superuser:
        return redirect('view_question', id=comment.question.id)

    question_id = comment.question.id
    comment.delete()
    messages.success(request, "Comment deleted successfully!")
    return redirect('view_question', id=question_id)


# Profile
@login_required
def profile(request):
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


# Remove Profile Pic
@login_required
def remove_profile_pic(request):
    if request.method == "POST":
        profile = request.user.profile
        profile.profile_picture.delete(save=False)
        profile.profile_picture = None
        profile.save()
    return redirect("profile")


# AI Suggestion View
@require_http_methods(["GET", "POST"])
def ai_suggest(request, question_id):
    try:
        question = get_object_or_404(Question, pk=question_id)

        text = (
            request.POST.get("text")
            or request.GET.get("text")
            or f"{getattr(question, 'title', '')}\n{getattr(question, 'body', '')}"
        ).strip()

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
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


def generate_suggestions(text: str):
    base = text[:80].replace("\n", " ")
    return [
        f"Clarify the problem scope related to: '{base}...'",
        "Share sample input/output so helpers can reproduce.",
        "Add relevant tags and environment details (OS, versions).",
    ]
