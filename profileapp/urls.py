from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_user, name='logout'),
     path('home/', views.home, name='home'),

    path('recruitment_form/', views.recruitment_form_view, name='recruitment_form'),
    path('recruitment_list/', views.recruitment_list_view, name='recruitment_list'),
    path('recruitment_detail/<int:pk>/', views.recruitment_detail_view, name='recruitment_detail'),
    path('success_page/', views.success_view, name='success_page'),

    # New paths for the login mechanism
    path('id/', views.enter_employee_id, name='enter_employee_id'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('set-password/', views.set_password, name='set_password'),
    path('login/', views.login_user, name='login'),
    path('expenses/', views.expense_list_view, name='expense_list'),
    path('expenses/export_excel/', views.export_expenses_excel, name='export_expenses_excel'),
    path('export_rrf_data_to_excel/', views.export_rrf_data_to_excel, name='export_rrf_data_to_excel'),
    path('search-managers/', views.search_managers, name='search_managers'),
    path('expense/view/<int:expense_id>/', views.view_expense_pdf, name='view_expense_pdf'),
    path('expense/', views.expense, name='expense'),

    path('noc-form/', views.noc_form_view, name='noc_form_view'),
    path('approve-noc-form/<int:form_id>/', views.approve_noc_form, name='approve_noc_form'),

]
