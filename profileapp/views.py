from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from .forms import ProfileForm, RecruitmentFormForm, VacancyDetailForm, EmployeeIDForm, OTPForm, SetPasswordForm,ExpenseForm,NOCForm
from .models import RecruitmentForm, VacancyDetail,Expense,User,AdditionalTraveler, NOC, NOCCountry, Employees, VisaType
from django.core.mail import send_mail
from django.conf import settings
from django.db import connection
from django.template.loader import render_to_string
from weasyprint import HTML
import random
from .decorators import unauthenticated_user, managers_only,rrf_employee_only,exec_dir_only
import pandas as pd
from datetime import date
from django.utils import timezone
from django.core.mail import EmailMessage
import os
from django.http import JsonResponse
from django.urls import reverse
import pusher


# Dashboard
@login_required(login_url='login')
@rrf_employee_only
@managers_only
def index(request):
    # Employee ID from logged-in user
    employee_id = request.user.username
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
    is_noc_admin = request.user.groups.filter(name="NOC Admin").exists()
    
    context = {
        'is_expense_admin': is_expense_admin,
        'is_rrf_admin': is_rrf_admin,
        'is_noc_admin':is_noc_admin,
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
                print(otp)
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
                [approved_by_email, 'ashraphy.tahmida@skf.transcombd.com', request.user.email],
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


# # NOC Form (ED Email)
def get_ed_email(department):
    # Custom SQL query to fetch email from `Executive_Directors` table based on department
    with connection.cursor() as cursor:
        cursor.execute("SELECT EDEmail FROM Executive_Directors WHERE Department = %s", [department])
        row = cursor.fetchone()
    if row:
        print(f"Email found: {row[0]}")
        return row[0]
    else:
        print(f"No email found for department: {department}")
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
            no_of_travelers = request.POST.get('no_of_travelers', '0')  # Default to '0' if empty
            
            try:
                no_of_travelers = int(no_of_travelers)  # Safely convert to integer
            except ValueError:
                no_of_travelers = 0  # If conversion fails, default to 0

            for i in range(no_of_travelers):
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

            # Send email notification to ED for approval
            employee_department = noc_instance.department
            ed_email = get_ed_email(employee_department)

            if ed_email:
                # Generate the approval link for the ED to approve
                approval_link = request.build_absolute_uri(reverse('approve_noc_form', args=[noc_instance.id]))

                email_body = (
                    f"A new {noc_instance.type} form has been submitted and is waiting for your approval.\n\n"
                    f"Click the link below to view the form details and approve:\n{approval_link}"
                )

                send_mail(
                    'Form Submission Notification',
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [ed_email],
                    fail_silently=False,
                )

                send_approval_notification(ed_email, employee_department)

            return redirect('noc_form_list')  # Redirect after submission

        else:
            print("Form is invalid. Errors:", noc_form.errors)

    else:
        # Autofill logic here
        employee_id = request.user.username  # Assuming EmployeeID is stored in username field

        # Fetch employee details from the Employees table
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT Name, Designation, Department, Email, Grade, Joining_Date
                FROM Employees
                WHERE EmployeeID = %s
            """, [employee_id])
            row = cursor.fetchone()

        # Set initial data for the form, including the joining_date
        initial_data = {
            'applicant_id': employee_id,
            'applicant_name': row[0] if row else '',
            'designation': row[1] if row else '',
            'department': row[2] if row else '',
            'email': row[3] if row else '',
            'grade': row[4] if row else '',
            'joining_date': row[5] if row else '',
        }

        # Initialize form with initial data
        noc_form = NOCForm(initial=initial_data)

    return render(request, 'profileapp/nocform.html', {'noc_form': noc_form})

# Approve NOC Form
@login_required(login_url='login')
@exec_dir_only
def approve_noc_form(request, form_id):
    noc_instance = get_object_or_404(NOC, id=form_id)
    additional_travelers = AdditionalTraveler.objects.filter(travel_recommendation=noc_instance)

    if request.method == 'POST':
        noc_instance.approved = True  # Mark as approved
        noc_instance.save()

        # Send a success message after approval
        

        return redirect('noc_form_list')  # Redirect to the list view

    return render(request, 'profileapp/approve_noc_form.html', {
        'noc_instance': noc_instance,
        'additional_travelers': additional_travelers,
    })

#NOC Form List
@login_required(login_url='login')  # Ensure user is logged in to access the page
def noc_form_list(request):
    user = request.user  # Get the logged-in user
    username = user.username  # Assuming the username is the EmployeeID

    is_ed = False  # Initialize is_ed to False by default

    # Check if the logged-in user is part of the 'noc admin' group
    if user.groups.filter(name='noc admin').exists():
        # If the user is part of the 'noc admin' group, show all NOC forms
        noc_forms = NOC.objects.all()
        is_noc_admin = True  # Mark the user as noc admin
    else:
        # Query to get the department of the logged-in user from the Employees table
        user_department = None
        with connection.cursor() as cursor:
            cursor.execute("SELECT Department FROM Employees WHERE EmployeeID= %s", [username])
            row = cursor.fetchone()
            if row:
                user_department = row[0]  # Assume department is stored in the first column

        # Check if the logged-in user is the ED for their department
        is_ed = False
        print(user_department)
        if user_department:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM Executive_Directors WHERE Department = %s AND EDID = %s", [user_department, username])
                result = cursor.fetchone()

                print(result)

                print(result)

                if result and result[0] > 0:
                    is_ed = True
                print(is_ed)
                print(is_ed)

        # Fetch NOC forms based on ED status
        if is_ed:
            # If the user is ED, fetch all NOC forms for their department
            print('ED')
            print('ED')
            noc_forms = NOC.objects.filter(department=user_department)
        else:
            # If the user is not ED, fetch only their own NOC forms
            noc_forms = NOC.objects.filter(applicant_id=username)

        is_noc_admin = False  # Mark the user as not noc admin

    # Pass 'is_noc_admin' to the template
    return render(request, 'profileapp/noc_form_list.html', {'noc_forms': noc_forms, 'is_noc_admin': is_noc_admin, 'is_ed': is_ed})

def view_noc_form(request, form_id):
    noc_instance = NOC.objects.get(id=form_id)
    additional_travelers = AdditionalTraveler.objects.filter(travel_recommendation=noc_instance)

    return render(request, 'profileapp/noc_template.html', {
        'noc_instance': noc_instance,
        'additional_travelers': additional_travelers,
    })

def send_approval_notification(executive_email, department_name):
    pusher_client = pusher.Pusher(
    app_id='1857539',
    key='0cc1f0e0cf6638ebb54f',
    secret='58b33235aa1ee1b8bb90',
    cluster='ap2',
    # ssl=True
)


    message = f"Need your approval for NOC form."

    # Create a unique channel name for the executive director
    # unique_channel_name = f"ed-channel-{executive_email.replace('@', '-').replace('.', '-')}"
    unique_channel_name = f"ed-channel-{executive_email}"
    
    # Trigger a Pusher event on the unique channel
    pusher_client.trigger(unique_channel_name, 'approval-event', {'message': message, 'email': executive_email})

@login_required(login_url='login')
def download_noc_pdf(request, noc_id):
    print("Function called with noc_id:", noc_id) 
    # Fetch the NOC instance
    noc_instance = get_object_or_404(NOC, id=noc_id)

    # Check if the form is approved
    if not noc_instance.approved:
        messages.error(request, "The form is not approved yet and cannot be downloaded.")
        return redirect('noc_form_list')

    # Debugging: Print the form type to confirm
    print(f"Form type: {noc_instance.type}")  # This should print either 'NOC' or 'Immigration'

    # Determine which PDF to generate based on the form type
    if noc_instance.type == 'NOC':
        return generate_noc_pdf(noc_instance)  # Generate NOC PDF
    elif noc_instance.type == 'Immigration':
        return generate_immigration_pdf(noc_instance)  # Generate Immigration PDF
    else:
        # If an unknown type is found, display an error
        messages.error(request, "Unknown form type. Cannot generate PDF.")
        return redirect('noc_form_list')

    
def generate_or_get_pdf_path(noc_instance):
    # This function should contain the logic to generate or retrieve the PDF path
    # For now, let's assume we generate a dummy path
    pdf_directory = 'pdfs/'
    if not os.path.exists(pdf_directory):
        os.makedirs(pdf_directory)
    pdf_path = os.path.join(pdf_directory, f"NOC_{noc_instance.id}.pdf")
    
    # Here you would generate the PDF and save it to pdf_path
    # For now, let's assume the PDF is already generated
    return pdf_path


# Generate NOC PDF
@login_required(login_url='login')
def generate_noc_pdf(request, noc_id):
    print("Generating NOC PDF") 
    # Fetch the NOC instance from the database
    noc_instance = get_object_or_404(NOC, id=noc_id)
    grade = noc_instance.grade.strip() if noc_instance.grade else ""

    # Fetch employee ID and visa type from NOC instance (assuming they are fields in your model)
    employee_id = noc_instance.applicant_id  # Adjust this if employee ID is stored differently
    visa_type = noc_instance.type_noc.lower()  # Adjust this if visa type is stored differently

    additional_travelers = noc_instance.additional_travelers.all()

    # Prepare the family members text if there are additional travelers
    if noc_instance.no_of_travelers > 0:
        travelers_list = [f"{traveler.relationship_with_traveler} named {traveler.additional_passport_name} bearing Passport No. {traveler.additional_passport_no}" for traveler in additional_travelers]
        family_members_text = ", ".join(travelers_list)
    else:
        family_members_text = ""

    # Fetch employee data based on applicant_id (EmployeeID)
    employee = Employees.objects.get(EmployeeID=noc_instance.applicant_id)

    # Determine pronouns based on gender
    if employee.Gender.lower() == 'male':
        pronoun_subjectC = 'He'
        pronoun_subjectS = 'he'
        pronoun_object = 'him'
        pronoun_possessive = 'his'
    elif employee.Gender.lower() == 'female':
        pronoun_subjectC = 'She'
        pronoun_subjectS = 'she'
        pronoun_object = 'her'
        pronoun_possessive = 'her'
    else:
        # Default to 'they/them' if gender is not specified or non-binary
        pronoun_subject = 'they'
        pronoun_object = 'them'
        pronoun_possessive = 'their'

    # Visa type ID dictionary
    visa_type_ids = {
        'tourist': '294',
        'business purpose': '345',
        'medical purpose': '556',
        'medical attendant': '789'
    }

    # Get specific visa type identifier from the dictionary
    visa_type_id = visa_type_ids.get(visa_type.lower(), '000')  # Default to '000' if visa type not found

    # Last four digits of Employee ID
    employee_last_digits = employee_id[-4:]

    # Current year
    current_year = timezone.now().year

    # Reference format
    reference_number = f"F & A-HR-VISA-{current_year}/{visa_type_id}/{employee_last_digits}"

    # Fetch the concern field for the selected country
    selected_country = noc_instance.country_visit
    try:
        noc_country = NOCCountry.objects.get(country=selected_country)
        concern = noc_country.concern  # Fetch the concern from NOCCountry model
        embassy = noc_country.embassy
        office_address = noc_country.office_address
    except NOCCountry.DoesNotExist:
        concern = "Concern not available"  # Default if no country is found
        embassy = "Embassy not available"
        office_address = "Address not available"

    selected_visatype = noc_instance.type_noc

    try:
        noc_visatype = VisaType.objects.get(visa = selected_visatype)
        subject = noc_visatype.subject
        cost_provider = noc_visatype.cost_provider
        intention = noc_visatype.intention

    except VisaType.DoesNotExist:
        subject = 'Not Available'
        cost_provider = 'None'
        intention = 'None'

    # Prepare the context with data from the NOC instance
    context = {
        'date': timezone.now().strftime("%d %B %Y"),  # Current date
        'designation': noc_instance.designation,
        'applicant_name': noc_instance.applicant_name,
        'applicant_id': employee_id,
        'passport_no': noc_instance.passport_no,
        'joining_date': noc_instance.joining_date.strftime("%d-%b-%Y"),
        'country_visit': noc_instance.country_visit,
        'travel_date_from': noc_instance.travel_date_from.strftime("%d %B %Y"),
        'travel_date_to': noc_instance.travel_date_to.strftime("%d %B %Y"),
        'grade': grade,  # Add grade to the context
        'reference_number': reference_number,  # Add reference number to the context
        'visa_type': visa_type,  # Add visa type to the context
        'concern': concern,  # Add the fetched concern to the context
        'embassy':embassy,
        'subject': subject,
        'cost_provider':cost_provider,
        'office_address': office_address,
        'family_members_text': family_members_text,  # Add family members text to context
        'pronoun_subjectC': pronoun_subjectC,
        'pronoun_subjectS': pronoun_subjectS,
        'pronoun_object': pronoun_object,   
        'pronoun_possessive': pronoun_possessive, 
        'intention' : intention,
    }

    # Render the HTML template with context data
    html_string = render_to_string('profileapp/noc_pdf_template.html', context)

    # Generate PDF using WeasyPrint
    pdf_file = HTML(string=html_string).write_pdf()

    # Return the PDF as a response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Travel_Recommendation.pdf"'

    return response

@login_required(login_url='login')
def generate_immigration_pdf(request, noc_id):
    # Fetch the NOC instance from the database
    noc_instance = get_object_or_404(NOC, id=noc_id)

    # Fetch employee data based on applicant_id (EmployeeID)
    employee = Employees.objects.get(EmployeeID=noc_instance.applicant_id)

    # Determine pronouns based on gender
    if employee.Gender.lower() == 'male':
        pronoun_subjectC = 'He'
        pronoun_subjectS = 'he'
        pronoun_object = 'him'
        pronoun_possessive = 'his'
    elif employee.Gender.lower() == 'female':
        pronoun_subjectC = 'She'
        pronoun_subjectS = 'she'
        pronoun_object = 'her'
        pronoun_possessive = 'her'
    else:
        # Default to 'they/them' if gender is not specified or non-binary
        pronoun_subject = 'they'
        pronoun_object = 'them'
        pronoun_possessive = 'their'

    # Fetch additional travelers for this NOC instance
    additional_travelers = AdditionalTraveler.objects.filter(travel_recommendation=noc_instance)

    # Prepare a list of all travelers including the main applicant
    all_travelers = []

    # Add the main applicant to the list
    all_travelers.append({
        'name': noc_instance.applicant_name,
        'passport_no': noc_instance.passport_no,
        'relationship': 'Self',  # You can specify 'Self' or leave it blank
    })

    # Add additional travelers to the list
    for traveler in additional_travelers:
        all_travelers.append({
            'name': traveler.additional_passport_name,
            'passport_no': traveler.additional_passport_no,
            'relationship': traveler.relationship_with_traveler,
        })

    selected_visatype = noc_instance.type_noc

    try:
        noc_visatype = VisaType.objects.get(visa = selected_visatype)
        cost_provider = noc_visatype.cost_provider
        intention = noc_visatype.intention

    except VisaType.DoesNotExist:
        cost_provider = 'None'
        intention = 'None'

    

    # Immigration-specific logic, similar to NOC but with changes to content
    context = {
        'date': timezone.now().strftime("%d %B %Y"),  # Current date
        'designation': noc_instance.designation,
        'applicant_name': noc_instance.applicant_name,
        'applicant_id': noc_instance.applicant_id,
        'passport_no': noc_instance.passport_no,
        'joining_date': noc_instance.joining_date.strftime("%d-%b-%Y"),
        'country_visit': noc_instance.country_visit,
        'travel_date_from': noc_instance.travel_date_from.strftime("%d %B %Y"),
        'travel_date_to': noc_instance.travel_date_to.strftime("%d %B %Y"),
        'pronoun_subjectC': pronoun_subjectC,  
        'pronoun_subjectS': pronoun_subjectS,
        'pronoun_object': pronoun_object,   
        'pronoun_possessive': pronoun_possessive,
        'all_travelers': all_travelers,  # Add the list of all travelers to the context
        'grade': noc_instance.grade,
        'port': noc_instance.port,
        'cost_provider' : cost_provider,
        'intention' : intention
    }

    # Immigration-specific HTML template
    html_string = render_to_string('profileapp/immigration_pdf_template.html', context)

    # Generate PDF using WeasyPrint
    pdf_file = HTML(string=html_string).write_pdf()

    print("Generate PDF")

    # Return the PDF as a response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Travel_Recommendation.pdf"'

    return response



@login_required(login_url='login')
def export_noc_to_excel(request):
    # Query the NOC data
    noc_data = NOC.objects.all().values(
        'id',  # Include 'id' for fetching related AdditionalTraveler records
        'applicant_id', 'applicant_name', 'designation', 'grade', 'department', 
        'joining_date', 'travel_date_from', 'travel_date_to', 'type', 'type_noc',
        'passport_name', 'passport_no', 'country_visit', 'no_of_travelers', 'approved', 
    )

    # Prepare data for export
    export_data = []

    for noc in noc_data:
        # Fetch additional travelers for this NOC
        additional_travelers = AdditionalTraveler.objects.filter(travel_recommendation_id=noc['id'])

        # Concatenate additional traveler information into single fields
        traveler_details = []
        for traveler in additional_travelers:
            traveler_info = f"{traveler.relationship_with_traveler} (Name: {traveler.additional_passport_name}, Passport No: {traveler.additional_passport_no})"
            traveler_details.append(traveler_info)
        
        # Join all traveler details into a single string
        traveler_details_str = "; ".join(traveler_details) if traveler_details else "None"

        # Prepare the row for the current NOC record including concatenated traveler details
        row = {
            'Applicant ID': noc['applicant_id'],
            'Applicant Name': noc['applicant_name'],
            'Designation': noc['designation'],
            'Grade': noc['grade'],
            'Department': noc['department'],
            'Joining Date': noc['joining_date'],
            'Travel Date From': noc['travel_date_from'],
            'Travel Date To': noc['travel_date_to'],
            'Type': noc['type'],
            'Visa Type': noc['type_noc'],
            'Passport Name': noc['passport_name'],
            'Passport No': noc['passport_no'],
            'Country to Visit': noc['country_visit'],
            'Number of Travelers': noc['no_of_travelers'],
            'Approved': noc['approved'],
            'Additional Travelers': traveler_details_str,  # Add concatenated traveler details
        }

        # Add the row to export data
        export_data.append(row)

    # Create a Pandas DataFrame from the export data
    df = pd.DataFrame(export_data)

    # Create an Excel file in memory
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="NOC_data.xlsx"'

    # Use Pandas to write the data to an Excel file
    df.to_excel(response, index=False, engine='openpyxl')

    return response
