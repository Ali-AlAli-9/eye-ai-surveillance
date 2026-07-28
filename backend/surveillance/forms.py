from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class CreateUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="كلمة المرور")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="تأكيد كلمة المرور")

    class Meta:
        model = User
        fields = ["username"]
        labels = {"username": "اسم المستخدم"}

    def clean(self):
        cleaned = super().clean()
        pwd = cleaned.get("password")
        conf = cleaned.get("confirm_password")
        if not pwd:
            raise forms.ValidationError("كلمة المرور مطلوبة")
        if not conf:
            raise forms.ValidationError("تأكيد كلمة المرور مطلوب")
        if pwd != conf:
            raise forms.ValidationError("كلمة المرور غير متطابقة")
        try:
            validate_password(pwd)
        except ValidationError as e:
            raise forms.ValidationError(list(e.messages))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
