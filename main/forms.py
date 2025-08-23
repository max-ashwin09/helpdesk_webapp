from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Question, Comment

#  Signup Form
class SignupForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'password1', 'password2']

#  OTP Form
class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6)

# ❓ Ask a Question Form
class QuestionForm(forms.ModelForm):
    file = forms.FileField(
        required=False,   # file optional kar diya
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
        })
    )

    class Meta:
        model = Question
        fields = ['title', 'description', 'file']  # sirf ye chahiye
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your question title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe your issue in detail'
            }),
        }


#  Comment Form
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content' , 'file']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write your comment...'}),
        }

#  Search Form
class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search questions...'
        })
    )



# Profile  control 
from django import forms
from .models import Profile

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_picture',]