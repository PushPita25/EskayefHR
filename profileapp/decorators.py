from django.shortcuts import redirect
from django.contrib import messages
from django.db import connection
from django.urls import reverse
from functools import wraps



def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):

        if request.user.is_authenticated:
            return redirect('home')
        else:
            return view_func(request, *args, **kwargs)
    
    return wrapper_func

def rrf_employee_only(view_func):
    def wrapper(request, *args, **kwargs):
        employee_id = request.user.username  
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1 
                FROM RRFEmployee 
                WHERE HODID = %s
            """, [employee_id])
            row = cursor.fetchone()

        
        if row:  
            request.is_rrf_employee = True
        else:
            request.is_rrf_employee = False

        return view_func(request, *args, **kwargs)

    return wrapper

def managers_only(view_func):
    def wrapper(request, *args, **kwargs):
        employee_id = request.user.username  
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1 
                FROM Employees 
                WHERE EmployeeID = %s AND (Grade IN ('M-1', 'M-2', 'M-3', 'M-4', 'M-5', 'M-6', 'ED') OR Grade = 'Manager')
            """, [employee_id])
            row = cursor.fetchone()

        
        if row:  
            request.is_manager = True
        else:
            request.is_manager = False

        return view_func(request, *args, **kwargs)

    return wrapper


def exec_dir_only(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get the employee ID from the username (assuming username is EmployeeID)
        employee_id = request.user.username  

        # Check if the user is in the Executive_Directors table
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1 
                FROM Executive_Directors 
                WHERE EDID = %s
            """, [employee_id])
            row = cursor.fetchone()

        if row:  
            # If the user is an Executive Director, proceed with the view
            return view_func(request, *args, **kwargs)
        else:
            # If the user is not an Executive Director, show a notification
            messages.error(request, "You do not have permission to view this page.")
            return redirect(reverse('dashboard'))  # Redirect to a relevant page (e.g., NOC form list or home)
        
    return wrapper
