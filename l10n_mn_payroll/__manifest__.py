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
    'name': 'Mongolian HR Payroll',
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
                 'account',
                 'om_hr_payroll_account',
                 'om_hr_payroll',
                 'hr_attendance',
                 'hr_expense',
                 'hr_holidays',
                 'hr_contract',
                 'om_account_accountant',
                 'l10n_mn_account'
                ],
    'data': [
            'data/account_journal_data.xml',
            'data/salary_rule_category_data.xml',
            'data/salary_rule_data.xml',
            'data/salary_rule_input_data.xml',
            'data/hr_hour_record_rule.xml',
            'data/location_data.xml',
            'data/country_data.xml',
            'data/ndd_type_data.xml',
            'data/vat_income_type_data.xml',
            'data/ir_config_parameter.xml',
            'data/cron_data.xml',
            'security/security_view.xml',
            'security/ir.model.access.csv',
            'views/sequence_view.xml',
            'views/absract_report_view.xml',
            'views/hr_hour_record_view.xml',
            'views/hr_resource_calendar_view.xml',
            'views/hr_payroll_prepayment_view.xml',
            'views/hr_contract_view.xml',
            'views/payroll_view.xml',
            'views/hr_leave_inherit_view.xml',
            'views/country_register_view.xml',
            'views/shift_holiday_register_view.xml',
            'views/payroll_bonus_view.xml',
            'views/working_day_register_view.xml',
            'views/insurance_type_view.xml',
            'views/work_category_view.xml',
            'views/location_register_view.xml',
            'views/vat_income_type_view.xml',
            'views/hr_payslip_run_inherit.xml',
            'views/hr_payslip_inherit_view.xml',
            'views/salary_mont_range_view.xml',
            'report/payroll_prepayment_report_view.xml',
            'wizard/hhoat_report_view.xml',
            'wizard/ndsh_report_import_view.xml',
            'wizard/hr_payroll_give_bank_report_view.xml',
            'wizard/hr_attendance_excel_report_view.xml',
            'wizard/hr_attendance_detail_excel_report_view.xml',
            'views/res_partner_bank_inherit_view.xml',
            'views/menu_view.xml',
    ],
    'assets':
        {
            'web.assets_backend': [
                'l10n_mn_payroll/static/src/js/stock_excel_report.js',
                'l10n_mn_payroll/static/src/js/no_format_integer.js',
                'l10n_mn_payroll/static/src/xml/no_format_integer.xml',
                'l10n_mn_payroll/static/src/scss/payslip_run.scss',
            ],
        },
    'installable': True,
    'application': False,
    'auto_install': False,
}
