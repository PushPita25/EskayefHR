from django.shortcuts import redirect
from django.contrib import messages
from django.db import connection


def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):

        if request.user.is_authenticated:
            return redirect('home')
        else:
            return view_func(request, *args, **kwargs)
    
    return wrapper_func

def managers_only(view_func):
    def wrapper(request, *args, **kwargs):
        employee_id = request.user.username  # Assuming employee ID is stored in the username
        
        # Raw SQL query to check if the employee has a grade of M-1 to M-6
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1 
                FROM Employees 
                WHERE EmployeeID = %s AND Grade IN ('M-1', 'M-2', 'M-3', 'M-4', 'M-5', 'M-6')
            """, [employee_id])
            row = cursor.fetchone()
        
        if row:  # Check if the employee is a manager
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You do not have permission to view this page.")
            return redirect('dashboard')  # Redirect to the dashboard
    return wrapper

def rrf_employee_only(view_func):
    def wrapper(request, *args, **kwargs):
        employee_id = request.user.username  # Assuming employee ID is stored in the username
        
        # Raw SQL query to check if the employee's ID matches any HODID in RRFEmployee table
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1 
                FROM RRFEmployee 
                WHERE HODID = %s
            """, [employee_id])
            row = cursor.fetchone()
        
        if row:  # Check if the user is an RRFEmployee
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You do not have permission to view this page.")
            return redirect('dashboard')  # Redirect to the dashboard
    return wrapper
