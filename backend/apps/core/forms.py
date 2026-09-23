from django import forms
from django.contrib.auth.forms import AuthenticationForm

from apps.core.base_forms import StyledForm, StyledModelForm
from apps.core.models import ALL_MODULES, Profile


class OwnerLoginForm(AuthenticationForm):
    """Single-owner login: the username is always "owner" and hidden — the
    user only ever sees a passcode field."""

    username = forms.CharField(widget=forms.HiddenInput(), initial="owner", required=False)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "input", "placeholder": "Passcode", "autofocus": True}),
        label="Passcode",
    )

    def clean_username(self):
        return "owner"

CURRENCY_CHOICES = [("MAD", "MAD — Moroccan Dirham"), ("USD", "USD — US Dollar"), ("EUR", "EUR — Euro"), ("GBP", "GBP — British Pound")]

# Each onboarding step is its own tiny form, staged into the session by
# OnboardingStepView and only ever written to the database in one atomic
# transaction at the final "complete" step (apps.core.views) — so closing
# LIFEOS mid-onboarding leaves zero trace (no partial User/Profile row) and
# relaunching just starts the wizard over. See docs on OnboardingCompleteView.


class OnboardingProfileForm(StyledForm):
    display_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"placeholder": "Alex", "autofocus": True}))
    theme = forms.ChoiceField(choices=Profile.THEME_CHOICES, initial="system")


class OnboardingSecurityForm(StyledForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Choose a passcode", "autofocus": True}), min_length=4)
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Confirm passcode"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("password") != cleaned.get("password_confirm"):
            self.add_error("password_confirm", "Passcodes don't match.")
        return cleaned


class OnboardingPersonalizeForm(StyledForm):
    """One BooleanField per module (rather than a single MultipleChoiceField)
    so each renders as its own styled checkbox row matching the design
    system's `.checkbox-input`, exactly like the mockup's ✓/☐ list."""

    tasks = forms.BooleanField(required=False, initial=True, label="Tasks")
    focus = forms.BooleanField(required=False, initial=True, label="Focus")
    finance = forms.BooleanField(required=False, initial=True, label="Finance")
    projects = forms.BooleanField(required=False, initial=True, label="Projects")
    people = forms.BooleanField(required=False, initial=True, label="People & Organizations")
    notes = forms.BooleanField(required=False, initial=True, label="Notes")
    school = forms.BooleanField(required=False, initial=False, label="School")
    journal = forms.BooleanField(required=False, initial=False, label="Journal")
    writing = forms.BooleanField(required=False, initial=False, label="Writing")
    calendar = forms.BooleanField(required=False, initial=False, label="Calendar")
    goals = forms.BooleanField(required=False, initial=False, label="Goals")

    def enabled_modules(self):
        return [key for key in ALL_MODULES if self.cleaned_data.get(key)]


class OnboardingFinanceForm(StyledForm):
    """Entirely optional — every field blank means "skip for now" (spec:
    distribution onboarding Finance step). Currency lives here rather than
    on the Profile step since it's only meaningful once Finance is in play."""

    default_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial="MAD")
    account_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"placeholder": "e.g. Main Bank (optional)"}))
    account_type = forms.ChoiceField(choices=[("bank", "Bank"), ("cash", "Cash")], required=False, initial="bank")
    opening_balance = forms.DecimalField(max_digits=14, decimal_places=2, required=False, initial=0)


class OnboardingSchoolForm(StyledForm):
    school_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"placeholder": "e.g. your school or university (optional)", "autofocus": True}))


class OnboardingProjectForm(StyledForm):
    project_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"placeholder": "e.g. a project you're working on (optional)", "autofocus": True}))


class PasscodeChangeForm(StyledForm):
    """Deliberately not django.contrib.auth.forms.PasswordChangeForm — same
    validation logic (old passcode must check out via the hasher, new ones
    must match), but with copy that matches "passcode" everywhere else in
    the UI rather than "password"."""

    current_password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Current passcode"}), label="Current passcode")
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "New passcode"}), label="New passcode", min_length=4)
    new_password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Confirm new passcode"}), label="Confirm new passcode")

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not self.user.check_password(value):
            raise forms.ValidationError("That's not your current passcode.")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password") and cleaned.get("new_password") != cleaned.get("new_password_confirm"):
            self.add_error("new_password_confirm", "New passcodes don't match.")
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["new_password"])
        self.user.save()
        return self.user


class AppearanceForm(StyledModelForm):
    class Meta:
        model = Profile
        fields = ["theme"]


class GeneralSettingsForm(StyledModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "default_currency", "school_name"]


AUTO_LOCK_CHOICES = [
    (0, "Immediately"),
    (1, "After 1 minute"),
    (5, "After 5 minutes"),
    (10, "After 10 minutes"),
    (30, "After 30 minutes"),
]


class AutoLockForm(StyledModelForm):
    auto_lock_minutes = forms.TypedChoiceField(choices=AUTO_LOCK_CHOICES, coerce=int, label="Lock after inactivity of")

    class Meta:
        model = Profile
        fields = ["auto_lock_minutes"]
