from django.core.management.base import BaseCommand
from profileapp.models import Employee, RRFEmployee, ExecutiveDirectors

class Command(BaseCommand):
    help = 'Seed the database with initial data'

    def handle(self, *args, **kwargs):
        # Seed Employee data
        employees_data = [
            {
                'EmployeeID': 101,
                'Name': 'Zarin Tasnim',
                'Unit': 'Talent Management',
                'Department': 'Commercial $ HR',
                'Grade': 'M-1',
                'Designation': 'Intern',
                'Email': 'pushpita.zarin@gmail.com',
                'ContactNo': '01786440010',
                'Location': 'OHQ',
                'Head_of_Dept': 'Md.Rafiqul Islam',
                'BU_Head': 'Mohammad Mostafa Hasan'
            },
            {
                'EmployeeID': 102,
                'Name': 'Arash Khan',
                'Unit': 'Talent Management',
                'Department': 'Commercial $ HR',
                'Grade': 'O-6',
                'Designation': 'Intern',
                'Email': 'arash25.khan@gmail.com',
                'ContactNo': '01786440007',
                'Location': 'OHQ',
                'Head_of_Dept': 'Md.Rafiqul Islam',
                'BU_Head': 'Mohammad Mostafa Hasan'
            },
            {
                'EmployeeID': 103,
                'Name': 'Rania Noor',
                'Unit': 'Talent Management',
                'Department': 'Commercial $ HR',
                'Grade': 'O-6',
                'Designation': 'Intern',
                'Email': 'zarin.pushpita@northsouth.edu',
                'ContactNo': '01786440020',
                'Location': 'OHQ',
                'Head_of_Dept': 'Md.Rafiqul Islam',
                'BU_Head': 'Mohammad Mostafa Hasan'
            }
        ]
        Employee.objects.bulk_create([Employee(**data) for data in employees_data])

        # Seed RRFEmployee data
        rrf_employee_data = [
            {
                'HODID': 102,
                'Name': 'Arash Khan',
                'Designation': 'Intern',
                'Unit': 'Talent Management',
                'Department': 'Commercial $ HR',
                'BU_Head': 'Mohammad Mostafa Hassan'
            },
            {
                'HODID': 102,
                'Name': 'Arash Khan',
                'Designation': 'Intern',
                'Unit': 'HR Operations',
                'Department': 'Commercial $ HR',
                'BU_Head': 'Mohammad Mostafa Hassan'
            }
        ]
        RRFEmployee.objects.bulk_create([RRFEmployee(**data) for data in rrf_employee_data])

        # Seed Executive Directors data
        executive_directors_data = [
            {'EDID': 1, 'EDDesg': 'Executive Director', 'EDEmail': 'munn@skf.transcombd.com'},
            {'EDID': 2, 'EDDesg': 'Executive Director-Finance', 'EDEmail': 'masud@skf.transcombd.com'},
            {'EDID': 3, 'EDDesg': 'Executive Director-Marketing & Sales', 'EDEmail': 'mislam@skf.transcombd.com'},
            {'EDID': 4, 'EDDesg': 'Executive Director-Plant', 'EDEmail': 'wahid@skf.transcombd.com'},
            {'EDID': 5, 'EDDesg': 'Executive Director-Technical', 'EDEmail': 'ikhtiar@skf.transcombd.com'},
            {'EDID': 6, 'EDDesg': 'Executive Director-Plant', 'EDEmail': 'arif@skf.transcombd.com'},
            {'EDID': 7, 'EDDesg': 'Executive Director-Quality Assurance', 'EDEmail': 'motiar@skf.transcombd.com'},
            {'EDID': 8, 'EDDesg': 'Executive Director-Commercial & HR', 'EDEmail': 'arash25.khan@gmail.com'},
        ]
        ExecutiveDirectors.objects.bulk_create([ExecutiveDirectors(**data) for data in executive_directors_data])

        self.stdout.write(self.style.SUCCESS('Successfully seeded the database'))
