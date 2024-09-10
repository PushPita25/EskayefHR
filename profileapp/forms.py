from django import forms
from .models import Profile, RecruitmentForm, VacancyDetail,Expense,NOC, AdditionalTraveler, NOCCountry, VisaType

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'profile_img': forms.FileInput(),
        }

class RecruitmentFormForm(forms.ModelForm):
    class Meta:
        model = RecruitmentForm
        fields = '__all__'
        exclude = ['user']

class VacancyDetailForm(forms.ModelForm):
    class Meta:
        model = VacancyDetail
        fields = '__all__'

class EmployeeIDForm(forms.Form):
    employee_id = forms.CharField(max_length=10, required=True)

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=4, required=True)

class SetPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 5:
            raise forms.ValidationError("Password must be at least 5 characters long.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        exclude = ['user']

class NOCForm(forms.ModelForm):
    class Meta:
        model = NOC
        fields = '__all__'  # Or specify the fields explicitly if needed

class AdditionalTravelerForm(forms.ModelForm):
    class Meta:
        model = AdditionalTraveler
        fields = '__all__'

class NOCForm(forms.ModelForm):
    country_visit = forms.ModelChoiceField(
        queryset=NOCCountry.objects.all(),
        label="Country to Visit",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a Country"
    )
    type_noc = forms.ModelChoiceField(
        queryset = VisaType.objects.all(),
        label= "Visa Type (if NOC)",
        widget = forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a Visa Type"

    )

    class Meta:
        model = NOC
        fields = '__all__'
