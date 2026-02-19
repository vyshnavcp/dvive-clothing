from django import forms
from .models import *


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content', 'image']
class TermsForm(forms.ModelForm):
    class Meta:
        model = TermsCondition
        fields = ["content"]
class PrivacyForm(forms.ModelForm):
    class Meta:
        model = PrivacyPolicy
        fields = ['content']