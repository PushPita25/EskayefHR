from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from .forms import ProfileForm, RecruitmentFormForm, VacancyDetailForm, EmployeeIDForm, OTPForm, SetPasswordForm,ExpenseForm,NOCForm
from .models import RecruitmentForm, VacancyDetail, Department,Expense,User,AdditionalTraveler, NOC
from django.core.mail import send_mail
from django.conf import settings
from django.db import connection
from django.template.loader import render_to_string
from weasyprint import HTML
import random
from .decorators import unauthenticated_user, managers_only,rrf_employee_only
import pandas as pd
from datetime import date
from django.utils import timezone
from django.core.mail import EmailMessage
import os
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse

# Dashboard
@login_required(login_url='login')
@rrf_employee_only
@managers_only
@rrf_employee_only
@managers_only
def index(request):
    # Employee ID from logged-in user
    employee_id = request.user.username
    is_rrf_employee = getattr(request, 'is_rrf_employee', False)
    is_manager = getattr(request, 'is_manager', False)
    is_rrf_employee = getattr(request, 'is_rrf_employee', False)
    is_manager = getattr(request, 'is_manager', False)
    
    # Fetching the corresponding name, designation, and department from the Employees table
    with connection.cursor() as cursor:
        cursor.execute("SELECT Name, Designation, Department FROM Employees WHERE EmployeeID = %s", [employee_id])
        row = cursor.fetchone()
    
    # Assign the fetched values to variables
    user_name = row[0] if row else employee_id
    user_designation = row[1] if row else ''
    user_department = row[2] if row else ''
    
    is_expense_admin = request.user.groups.filter(name="Expense Admin").exists()
    is_rrf_admin = request.user.groups.filter(name="RRF Admin").exists()
    
    context = {
        'is_expense_admin': is_expense_admin,
        'is_rrf_admin': is_rrf_admin,
        'user_name': user_name,  # Pass the name to the template
        'user_designation': user_designation,  # Pass the designation to the template
        'user_department': user_department,  # Pass the department to the template
        'is_rrf_employee': is_rrf_employee,
        'is_manager': is_manager,
       
    }
    return render(request, 'profileapp/dashboard.html', context)
def home(request):
    return render(request, 'profileapp/dashboard.html')

#Login 
@unauthenticated_user
def login_user(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        password = request.POST.get('password')
        user = authenticate(request, username=employee_id, password=password)

        if user is not None:
            employee_name = get_name_by_employee_id(employee_id)  
            if employee_name:
                login(request, user)
                # messages.info(request, f'Welcome back, {employee_name}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Employee name not found.')
                return redirect('login')
        else:
            # Custom error messages based on the situation
            if not User.objects.filter(username=employee_id).exists():
                messages.error(request, 'Employee ID does not exist.')
            else:
                messages.error(request, 'Invalid password.')
            return redirect('login')
    else:
        # If redirected after setting password, show success message
        if 'Your password is set successfully.' in messages.get_messages(request):
            messages.info(request, 'Your password is set successfully.')
    return render(request, 'profileapp/login_page.html')


#Enter Employee ID
@unauthenticated_user
def enter_employee_id(request):
    if request.method == 'POST':
        form = EmployeeIDForm(request.POST)
        if form.is_valid():
            employee_id = form.cleaned_data['employee_id']
            email = get_email_by_employee_id(employee_id)
            name = get_name_by_employee_id(employee_id)  # Fetch the employee name
            if email:
                otp = send_otp(email)
                request.session['otp'] = otp
                request.session['employee_id'] = employee_id
                request.session['employee_name'] = name  # Store name in session
                return redirect('verify_otp')
            else:
                messages.error(request, 'Employee ID not found.')
    else:
        form = EmployeeIDForm()
    return render(request, 'profileapp/enter_employee_id.html', {'form': form})


#VerifyOTP
@unauthenticated_user
def verify_otp(request):
    name = request.session.get('employee_name')  # Get employee name from session
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            if entered_otp == str(request.session.get('otp')):
                return redirect('set_password')
            else:
                messages.error(request, 'Invalid OTP.')
    else:
        form = OTPForm()
    messages.success(request, f'Hello, {name}! Please check your email and provide the OTP')  # Send thank you message
    return render(request, 'profileapp/verify_otp.html', {'form': form})

#SetPassword
@unauthenticated_user
def set_password(request):
    name = request.session.get('employee_name')  # Get the employee name from session
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            employee_id = request.session.get('employee_id')
            user = create_user_with_password(employee_id, password)
            if user:
                messages.success(request, 'Your password is set successfully.')  # Success message for login page
                request.session.flush()
                return redirect('login')
        else:
            messages.error(request, 'Password must be at least 5 characters long.')
    else:
        form = SetPasswordForm()
        messages.info(request, f'Dear {name}, please set your password.')  # Notification for set_password page
    return render(request, 'profileapp/set_password.html', {'form': form})


#GetEmailByEmployeeID
def get_email_by_employee_id(employee_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT Email FROM Employees WHERE EmployeeID = %s", [employee_id])
        row = cursor.fetchone()
    return row[0] if row else None

#SendOTP
def send_otp(email):
    otp = random.randint(1000, 9999)
    send_mail(
        'Your OTP Code',
        f'Your OTP code is {otp}',
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    return otp

#CreateUser
def create_user_with_password(employee_id, password):
    email = get_email_by_employee_id(employee_id)
    if email:
        user, created = User.objects.get_or_create(username=employee_id, email=email)
        user.set_password(password)
        user.save()
        return user
    return None

#GetNameByEmployeeID
def get_name_by_employee_id(employee_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT Name FROM Employees WHERE EmployeeID = %s", [employee_id])
        row = cursor.fetchone()
    return row[0] if row else None

#Logout
@login_required(login_url='login')
def logout_user(request):
    logout(request)
    messages.info(request, 'You logged out successfully')
    return redirect('login')


#Success message
@login_required(login_url='login')
def success_view(request):
    return render(request, 'profileapp/success.html')


#Profile
@login_required(login_url='login')
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'{request.user.username}, Your Profile is Updated')
            return redirect('/')
    else:
        form = ProfileForm(instance=request.user.profile)
    context = {'form': form}
    return render(request, 'profileapp/profile.html', context)

@login_required(login_url='login')
def success_view(request):
    return render(request, 'profileapp/success.html')


def get_units(employee_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT Unit FROM RRFEmployee WHERE HODID = %s", [employee_id])
        units = cursor.fetchall()
    return [unit[0] for unit in units] if units else []

#RecruitmentFormView
@login_required(login_url='login')
@rrf_employee_only
def recruitment_form_view(request):
    if request.method == 'POST':
        form = RecruitmentFormForm(request.POST)
        if form.is_valid():
            recruitment_form_instance = form.save(commit=False)
            recruitment_form_instance.user = request.user
            recruitment_form_instance.save()

            # Save vacancy details
            row_count = int(request.POST.get('row_count', '0'))
            for i in range(1, row_count + 1):
                vacancy_data = {
                    'recruitment_form': recruitment_form_instance,
                    'vacancy_type': request.POST.get(f'vacancy_type_{i}'),
                    'resigned_name': request.POST.get(f'resigned_name_{i}'),
                    'employee_id': request.POST.get(f'employee_id_{i}'),
                    'designation': request.POST.get(f'designation_{i}'),
                    'resignation_date': request.POST.get(f'resignation_date_{i}'),
                    'last_date': request.POST.get(f'last_date_{i}'),
                }
                VacancyDetail.objects.create(**vacancy_data)

            # Fetch email by designation
            approved_by_email = get_email_by_designation(recruitment_form_instance.approved_by)
            if not approved_by_email:
                messages.error(request, 'The designated approver does not have an associated email.')
                return redirect('recruitment_form')

            # Generate PDF
            html_string = render_to_string('profileapp/recruitment_detail_pdf.html', {'recruitment_form': recruitment_form_instance})
            pdf_file = HTML(string=html_string).write_pdf()

            
            subject = f'RRF - {recruitment_form_instance.department} - No. Of Vacant Position: {recruitment_form_instance.vacant_position}'

            email_body = (
                f"RRF - {recruitment_form_instance.department} - {recruitment_form_instance.designation}_No. Of Vacant Position:{recruitment_form_instance.vacant_position} has been submitted"
            )

            
            # Send email with PDF attachment
            email = EmailMessage(
                subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                # [approved_by_email, 'ashraphy.tahmida@skf.transcombd.com', request.user.email],
                [approved_by_email, 'zarin.pushpita@northsouth.edu', request.user.email],
            )
            email.attach('Recruitment_Form.pdf', pdf_file, 'application/pdf')
            email.send()
            messages.success(request, 'Recruitment form submitted successfully!')

            # Redirect to dashboard if user is not an admin
            if not request.user.groups.filter(name="RRF Admin").exists():
                return redirect('dashboard')

            return redirect('recruitment_list')
    else:
        employee_id = request.user.username  
        units = get_units(employee_id)
        with connection.cursor() as cursor:
            cursor.execute("SELECT Name, Department FROM Employees WHERE EmployeeID = %s", [employee_id])
            row = cursor.fetchone()
        initial_data = {
            'raised_by': row[0] if row else '',
            'department': row[1] if row else '',
            'date': date.today().isoformat(),  
        }
        form = RecruitmentFormForm(initial=initial_data)
    return render(request, 'profileapp/recruitment_form.html', {'form': form, 'units': units})


# GetEmailByDesignation
def get_email_by_designation(designation):
    with connection.cursor() as cursor:
        cursor.execute("SELECT EDEmail FROM Executive_Directors WHERE EDDesg = %s", [designation])
        row = cursor.fetchone()
    return row[0] if row else None

#RecruitmentFormList
@login_required(login_url='login')
def recruitment_list_view(request):
    is_rrf_admin = request.user.groups.filter(name="RRF Admin").exists()
    
    if is_rrf_admin:
        recruitment_forms = RecruitmentForm.objects.all()
        context = {
            'recruitment_forms': recruitment_forms,
            'is_rrf_admin': is_rrf_admin,
        }
        return render(request, 'profileapp/recruitment_list.html', context)
    else:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')



#EmailByDesignation
def get_email_by_designation(designation):
    with connection.cursor() as cursor:
        cursor.execute("SELECT EDEmail FROM Executive_Directors WHERE EDDesg = %s", [designation])
        row = cursor.fetchone()
    return row[0] if row else None

#SendNotification
def send_notification(email, username, additional_recipients=[]):
    subject = 'New Recruitment Form Submitted'
    message = f'Hi, {username} has submitted the form.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email] + additional_recipients
    send_mail(subject, message, from_email, recipient_list)

#RecruitmentDetailView
@login_required(login_url='login')
def recruitment_detail_view(request, pk):
    recruitment_form = get_object_or_404(RecruitmentForm, pk=pk)
    if request.user.groups.filter(name="RRF Admin").exists():
        return render(request, 'profileapp/recruitment_detail.html', {'recruitment_form': recruitment_form})
    else:
        messages.error(request, 'You do not have permission to view this form.')
        return redirect('home')

# DownloadPDF
# @login_required(login_url='login')
# def download_pdf(request, pk):
#     recruitment_form = get_object_or_404(RecruitmentForm, pk=pk, user=request.user)
#     html_string = render_to_string('profileapp/recruitment_detail_pdf.html', {'recruitment_form': recruitment_form})
#     html = HTML(string=html_string)
#     pdf = html.write_pdf()
#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename=recruitment_detail_{pk}.pdf'
#     return response


#ExpenseReport
def expense(request):
    return render(request, 'profileapp/expense.html')

@login_required(login_url='login')
@managers_only
def expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense_instance = form.save(commit=False)
            expense_instance.user = request.user  
            expense_instance.save()
            
            # Generate PDF
            html_string = render_to_string('profileapp/expense_pdf_template.html', {'expense': expense_instance})
            pdf_file = HTML(string=html_string).write_pdf()

            # Success message after form submission
            messages.success(request, 'Your Expense Report is submitted Successfully.')
            messages.success(request, 'Your Expense Report is submitted Successfully.')

            # Clear the form
            form = ExpenseForm()

            # Render the form again with the success message
            response = render(request, 'profileapp/expense.html', {'form': form})

            # Attach the PDF download header
            response['Content-Disposition'] = f'attachment; filename="expense_report_{expense_instance.id}.pdf"'
            response.content = pdf_file

            return response  # Download PDF directly after submission

    else:
        employee_id = request.user.username  
        with connection.cursor() as cursor:
            cursor.execute("SELECT Name, Designation, Department, Unit, Location FROM Employees WHERE EmployeeID = %s", [employee_id])
            row = cursor.fetchone()
        initial_data = {
            'id_no': employee_id,
            'name': row[0] if row else '',
            'designation': row[1] if row else '',
            'department': row[2] if row else '',
            'unit': row[3] if row else '',
            'location': row[4] if row else '',
        }
        form = ExpenseForm(initial=initial_data)
    
    return render(request, 'profileapp/expense.html', {'form': form})


#ExpenseList
@login_required(login_url='login')
def expense_list_view(request):
    if request.user.groups.filter(name="Expense Admin").exists():
        expenses = Expense.objects.all() 
        return render(request, 'profileapp/expense_list.html', {'expenses': expenses})
    else:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')
    
#Expense List Filters 
@login_required(login_url='login')
def search_managers(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        query = request.GET.get('term', '')
        expenses = Expense.objects.filter(name__icontains=query)  # Search by name
        results = [{'name': expense.name} for expense in expenses]
        return JsonResponse(results, safe=False)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

#view expense pdf
@login_required(login_url='login')
def view_expense_pdf(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)  # Fetch the specific expense by ID
    
    # Render the PDF template with the expense context
    html_string = render_to_string('profileapp/expense_pdf_template.html', {'expense': expense})
    pdf_file = HTML(string=html_string).write_pdf()

    # Serve the PDF as an HTTP response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="expense_{expense_id}.pdf"'

    return response

#ExportExpenseExcel
@login_required(login_url='login')
def export_expenses_excel(request):
    # Fetch all form data excluding the 'id' field
    data = Expense.objects.all().values(
        'id_no', 'name', 'designation', 'department', 'month', 'unit', 'location',
        'utility', 'utility_remarks', 'driver_wages', 'driver_wages_remarks',
        'service_staff_wages', 'service_staff_wages_remarks', 'security_staff_wages',
        'security_staff_wages_remarks', 'leave_fare_assistance', 'leave_fare_assistance_remarks',
        'fuel_cost', 'fuel_cost_remarks', 'gas_cost', 'gas_cost_remarks',
        'repair_maintenance', 'repair_maintenance_remarks', 'tyres', 'tyres_remarks',
        'battery', 'battery_remarks', 'car_denting_painting', 'car_denting_painting_remarks',
        'car_decorations', 'car_decorations_remarks', 'toll', 'toll_remarks',
        'others', 'others_remarks', 'telephone', 'telephone_remarks',
        'mobile_set', 'mobile_set_remarks', 'medical_expense', 'medical_expense_remarks',
        'medical_expense_surgery', 'medical_expense_surgery_remarks',
        'total_taka', 'advance', 'expenses_as_above', 'amount_due'
    )

    # Convert the queryset to a DataFrame
    # Fetch all form data excluding the 'id' field
    data = Expense.objects.all().values(
        'id_no', 'name', 'designation', 'department', 'month', 'unit', 'location',
        'utility', 'utility_remarks', 'driver_wages', 'driver_wages_remarks',
        'service_staff_wages', 'service_staff_wages_remarks', 'security_staff_wages',
        'security_staff_wages_remarks', 'leave_fare_assistance', 'leave_fare_assistance_remarks',
        'fuel_cost', 'fuel_cost_remarks', 'gas_cost', 'gas_cost_remarks',
        'repair_maintenance', 'repair_maintenance_remarks', 'tyres', 'tyres_remarks',
        'battery', 'battery_remarks', 'car_denting_painting', 'car_denting_painting_remarks',
        'car_decorations', 'car_decorations_remarks', 'toll', 'toll_remarks',
        'others', 'others_remarks', 'telephone', 'telephone_remarks',
        'mobile_set', 'mobile_set_remarks', 'medical_expense', 'medical_expense_remarks',
        'medical_expense_surgery', 'medical_expense_surgery_remarks',
        'total_taka', 'advance', 'expenses_as_above', 'amount_due'
    )

    # Convert the queryset to a DataFrame
    df = pd.DataFrame(list(data))

    # Define the HttpResponse with Excel content type

    # Define the HttpResponse with Excel content type
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="expenses.xlsx"'

    # Write the DataFrame to Excel file

    # Write the DataFrame to Excel file
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Expenses')
    return response

#RRF to excel
@login_required(login_url='login')
def export_rrf_data_to_excel(request):
    if not request.user.groups.filter(name="RRF Admin").exists():
        messages.error(request, "You do not have permission to export this data.")
        return redirect('home')

    recruitment_forms = RecruitmentForm.objects.all()
    data = []

    for form in recruitment_forms:
        vacancy_details = VacancyDetail.objects.filter(recruitment_form=form)
        for vacancy in vacancy_details:
            data.append({
                "Requisition Raised By": form.raised_by,
                "Department": form.department,
                "Date": form.date,
                "Unit Name": form.unit_name,
                "Designation/Job Title": form.designation,
                "Recruitment Type": form.recruitment_type,
                "Number of Vacant Positions": 1,  # Here we are ensuring each vacancy is represented in its own row
                "Job Role": form.job_role,
                "Location": form.location,
                "Vacancy Type": vacancy.vacancy_type,
                "Resigned Name": vacancy.resigned_name,
                "Employee ID": vacancy.employee_id,
                "Designation": vacancy.designation,
                "Resignation Date": vacancy.resignation_date,
                "Last Date at Office": vacancy.last_date,
            })

    df = pd.DataFrame(data)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="recruitment_data.xlsx"'
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Recruitment Data')

    return response

#NOC Form
# @login_required(login_url='login')
# def noc_form_view(request):
#     if request.method == 'POST':
#         noc_form = NOCForm(request.POST, request.FILES)

#         if noc_form.is_valid():
#             noc_instance = noc_form.save()

#             # Handle additional travelers dynamically
#             no_of_travelers = request.POST.get('no_of_travelers', 0)

#             for i in range(int(no_of_travelers)):
#                 relationship = request.POST.get(f'relationship_{i + 1}')
#                 additional_passport_name = request.POST.get(f'additional_passport_name_{i + 1}')
#                 additional_passport_no = request.POST.get(f'additional_passport_no_{i + 1}')
#                 additional_passport_copy = request.FILES.get(f'additional_passport_copy_{i + 1}')

#                 if relationship and additional_passport_name and additional_passport_no:
#                     AdditionalTraveler.objects.create(
#                         travel_recommendation=noc_instance,
#                         relationship_with_traveler=relationship,
#                         additional_passport_name=additional_passport_name,
#                         additional_passport_no=additional_passport_no,
#                         additional_passport_copy=additional_passport_copy,
#                     )

#             return redirect('success_page')
#         else:
#             # Print errors for debugging
#             print("Form is invalid. Errors:", noc_form.errors)

#     else:
#         # Autofill logic here
#         employee_id = request.user.username

#         # Fetch employee details from the Employees table
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT Name, Designation, Department
#                 FROM Employees
#                 WHERE EmployeeID = %s
#             """, [employee_id])
#             row = cursor.fetchone()

#         # Set initial data for the form
#         initial_data = {
#             'applicant_id': employee_id,
#             'applicant_name': row[0] if row else '',
#             'designation': row[1] if row else '',
#             'department': row[2] if row else '',
#             # # Example: 'joining_date': row[3] if row else '',  # Uncomment if you fetch joining_date
#             # 'unit': row[3] if row else '',
#             # 'location': row[4] if row else '',
#         }

#         # Initialize form with initial data
#         noc_form = NOCForm(initial=initial_data)

#     return render(request, 'profileapp/nocform.html', {'noc_form': noc_form})


# #Generate NOC PDF
# @login_required(login_url='login')
# def generate_noc_pdf(request, noc_id):
#     # Fetch the NOC instance from the database
#     noc_instance = get_object_or_404(NOC, id=noc_id)

#     # Prepare the context with data from the NOC instance
#     context = {
#         'date': timezone.now().strftime("%d %B %Y"),  # Current date
#         'designation': noc_instance.designation,
#         'applicant_name': noc_instance.applicant_name,
#         'applicant_id': noc_instance.applicant_id,
#         'passport_no': noc_instance.passport_no,
#         'joining_date': noc_instance.joining_date.strftime("%d-%b-%Y"),
#         'country_visit': noc_instance.country_visit,
#         'travel_date_from': noc_instance.travel_date_from.strftime("%d %B %Y"),
#         'travel_date_to': noc_instance.travel_date_to.strftime("%d %B %Y")
#     }

#     # Render the HTML template with context data
#     html_string = render_to_string('profileapp/noc_pdf_template.html', context)

#     # Generate PDF using WeasyPrint
#     pdf_file = HTML(string=html_string).write_pdf()

#     # Return the PDF as a response
#     response = HttpResponse(pdf_file, content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="noc_{noc_instance.id}.pdf"'

#     return response




# NOC Form (ED Email)
def get_ed_email(department):
    # Custom SQL query to fetch email from `Executive_Directors` table based on department
    with connection.cursor() as cursor:
        cursor.execute("SELECT EDEmail FROM Executive_Directors WHERE Department = %s", [department])
        row = cursor.fetchone()
    if row:
        return row[0]
    else:
        return None

# NOC Form
@login_required(login_url='login')
def noc_form_view(request):
    if request.method == 'POST':
        noc_form = NOCForm(request.POST, request.FILES)

        if noc_form.is_valid():
            noc_instance = noc_form.save(commit=False)
            noc_instance.approved = False  # Initially set approved to False
            noc_instance.save()

            # Handle additional travelers dynamically
            no_of_travelers = request.POST.get('no_of_travelers', 0)

            for i in range(int(no_of_travelers)):
                relationship = request.POST.get(f'relationship_{i + 1}')
                additional_passport_name = request.POST.get(f'additional_passport_name_{i + 1}')
                additional_passport_no = request.POST.get(f'additional_passport_no_{i + 1}')
                additional_passport_copy = request.FILES.get(f'additional_passport_copy_{i + 1}')

                if relationship and additional_passport_name and additional_passport_no:
                    AdditionalTraveler.objects.create(
                        travel_recommendation=noc_instance,
                        relationship_with_traveler=relationship,
                        additional_passport_name=additional_passport_name,
                        additional_passport_no=additional_passport_no,
                        additional_passport_copy=additional_passport_copy,
                    )

            # Send email notification to the corresponding Executive Director
            employee_department = noc_instance.department
            ed_email = get_ed_email(employee_department)

            if ed_email:
                # Generate the approval link for the email
                approval_link = request.build_absolute_uri(
                    reverse('approve_noc_form', args=[noc_instance.id])
                )

                email_body = (
                    f"A new NOC form has been submitted and is waiting for your approval.\n\n"
                    f"Click the link below to view the form details and approve:\n{approval_link}"
                )

                send_mail(
                    'NOC Form Submission Notification',
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,  # Use default from email
                    [ed_email],
                    fail_silently=False,
                )

                # Send Pusher notification for real-time update
                send_approval_notification(ed_email, employee_department)

            return redirect('noc_form_list')  # Redirect to list page after submission
        else:
            print("Form is invalid. Errors:", noc_form.errors)

    else:
        # Autofill logic here
        employee_id = request.user.username  # Assuming EmployeeID is stored in username field

        # Fetch employee details from the Employees table
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT Name, Designation, Department, Email
                FROM Employees
                WHERE EmployeeID = %s
            """, [employee_id])
            row = cursor.fetchone()

        # Set initial data for the form
        initial_data = {
            'applicant_id': employee_id,
            'applicant_name': row[0] if row else '',
            'designation': row[1] if row else '',
            'department': row[2] if row else '',
            'email': row[3] if row else '',
        }

        # Initialize form with initial data
        noc_form = NOCForm(initial=initial_data)

    return render(request, 'profileapp/nocform.html', {'noc_form': noc_form})

# Approve NOC Form
def approve_noc_form(request, form_id):
    noc_instance = NOC.objects.get(id=form_id)
    additional_travelers = AdditionalTraveler.objects.filter(travel_recommendation=noc_instance)

    if request.method == 'POST':
        noc_instance.approved = True
        noc_instance.save()
        # messages.success(request, 'The NOC form has been approved successfully.')
        return redirect('noc_form_list')  # Redirect to the list view

    return render(request, 'profileapp/approve_noc_form.html', {
        'noc_instance': noc_instance,
        'additional_travelers': additional_travelers,
    })


#NOC Form List
@login_required(login_url='login')  # Ensure user is logged in to access the page
def noc_form_list(request):
    user = request.user  # Get the logged-in user
    noc_forms = NOC.objects.filter(applicant_id=user.username)  # Assuming applicant_id stores EmployeeID (username)

    return render(request, 'profileapp/noc_form_list.html', {'noc_forms': noc_forms})



def view_noc_form(request, form_id):
    noc_instance = NOC.objects.get(id=form_id)
    additional_travelers = AdditionalTraveler.objects.filter(travel_recommendation=noc_instance)

    return render(request, 'profileapp/noc_template.html', {
        'noc_instance': noc_instance,
        'additional_travelers': additional_travelers,
    })


import pusher



def send_approval_notification(executive_email, department_name):
    pusher_client = pusher.Pusher(
    app_id='1857539',
    key='0cc1f0e0cf6638ebb54f',
    secret='58b33235aa1ee1b8bb90',
    cluster='ap2',
    ssl=True
    )
    message = f"Department: {department_name} - Need your approval for NOC form."

    # Create a unique channel name for the executive director
    unique_channel_name = f"ed-channel-{executive_email.replace('@', '-').replace('.', '-')}"
    
    # Trigger a Pusher event on the unique channel
    pusher_client.trigger(unique_channel_name, 'approval-event', {'message': message, 'email': executive_email})
