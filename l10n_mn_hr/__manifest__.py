# -*- coding: utf-8 -*-
##############################################################################
#
#    AIBI LLC, Enterprise Management Solution    
#    Copyright (C) 2021-2024 AIBI LLC Co.,ltd (<http://www.aibi.mn>). 
#    All Rights Reserved
#
#    Address : Bayanzurkh District, Dalai Tower, 803, AIBI LLC
#    Email : aibillc@gmail.com
#    Phone : 976 + 99169117
#
##############################################################################

{
    'name': 'Mongolian HR',
    'version': '1.0',
    'category': 'hr',
    'sequence': 35,
    'author': 'AIBI Developer Team',
    'license': 'AGPL-3',
    'summary': 'Human resource additional development',
    'description': """Mongolian hr additional module""",
    'website': 'www.aibi.mn',
    'depends': [
                 'base',
                 'hr',
                 'hr_attendance',
                 'om_hr_payroll',
                 'hr_expense',
                 'hr_holidays',
                 'hr_contract',
                 'hr_recruitment',
                 'hr_skills',
                 'hr_org_chart',
                 'resource',
                 'l10n_mn_vat',
                 'l10n_mn_payroll',
                 'survey'
                ],
    'data': [ 
            'data/education_data.xml',  
            'data/driver_type_data.xml',
            'data/language_data.xml',
            'data/sequence_data.xml',
            'data/decree_template_data.xml',
            'data/resource_calendar_data.xml',
            'data/cron_data.xml',
            'data/contract_decree_conf_data.xml',
            'security/security_view.xml',
            'security/ir.model.access.csv',
            'report/decree_report_view.xml',
            'report/routing_slip_report.xml',
            'report/reference_report_view.xml',
            'report/handover_act_report_view.xml',
            'report/report_view.xml',
            'views/new_hr_employee_view.xml',
            'views/mn_hr_inherit_view.xml',
            'views/driver_type_view.xml',
            'views/hr_decree_view.xml',
            'views/hr_penalty.xml',
            'views/language_type_view.xml',
            'views/computer_type_view.xml',
            'views/education_degree_type_view.xml',
            'views/training_order.xml',
            'views/routing_slip_view.xml',
            'views/work_handover_act_view.xml',
            'views/contract_type_register.xml', 
            'views/other_contracts.xml' ,
            'views/employee_transfer_view.xml',
            'views/reference_register_view.xml',
            'views/dismiss_register_view.xml',
            'views/employee_request_register_view.xml',
            'views/job_appointment_register_view.xml',
            'views/workplace_register_view.xml',
            'views/training_fee_options_view.xml',
            'views/hr_applicant_inherit_view.xml',
            'views/hr_department_view.xml',
            'views/work_location_view.xml',
            'views/hr_job_view.xml',
            'views/applicant_register_view.xml', 
            'views/reference_register_type_view.xml',
            'views/decree_register_type_view.xml',
            'views/hr_overtime_view.xml',
            'views/kpi_template_view.xml',
            'views/employee_kpi_view.xml',
            'views/contract_decree_configuration.xml',
            'views/menu_view.xml',
    ],
    'test': [
        'tests/test_abnormal_register.py',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
