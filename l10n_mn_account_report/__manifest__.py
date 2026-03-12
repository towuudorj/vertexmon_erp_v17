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
    'name': 'Mongolian Account Standart Report',
    'version': '1.0',
    'category': 'Accounting',
    'sequence': 35,
    'author': 'AIBI Developer Team',
    'license': 'AGPL-3',
    'summary': 'Financial and Analytic Accounting',
    'description': """Mongolian account standart report additional module""",
    'website': 'www.aibi.mn',
    'depends': [
                'account',
                'sales_team',
                'analytic',
                'om_account_accountant',
                'account_statement_base',
                'om_fiscal_year',
                'vertexmon_tools'
                ],
    'data': [
            'data/account_balance_type_data.xml',
            'data/account_income_type_data.xml',
            'data/report_group_option_data.xml',
            'security/security_view.xml',
            'security/ir.model.access.csv',
            'views/print_cash_order.xml',
            'views/bank_and_cash_statement_view.xml',
            'views/payment_order_view.xml',
            'report/payment_order.xml',
            'report/payment_order_transport.xml',
            'views/report_view.xml',
            'views/cash_move_report_view.xml',
            'views/general_book_report_view.xml',
            'views/general_journal_report_view.xml',
            'views/absract_report_view.xml',
            'views/account_move_analysis_view.xml',
            'views/general_journal_report_two_view.xml',
            'views/general_book_report_two_view.xml',
            'views/balance_sheet_excel_report_view.xml',
            'views/equity_excel_report_view.xml',
            'views/profit_excel_view.xml',
            'views/statement_cash_flow_excel_report_view.xml',
            'views/account_balance_type_view.xml',
            'views/account_income_type_view.xml',
            'views/equity_configure_view_report.xml',
            'views/account_account_inherit_view.xml',
            'wizard/account_partner_ledger_excel_report.xml',
            'views/multi_company_balance_sheet_view.xml',
            'views/menu_view.xml',
            

    ],
    'assets': {
        'web.assets_backend': [
            'l10n_mn_account_report/static/src/css/*.css'
        ]
    },
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
