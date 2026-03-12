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
    'name': 'Mongolian Account',
    'version': '1.0',
    'category': 'Accounting',
    'sequence': 35,
    "author" : "AIBI Development Team",
    'license': 'AGPL-3',
    'summary': 'Financial and Analytic Accounting',
    'description': """Mongolian account additional module""",
    'website': 'www.aibi.mn',
    'depends': [
                'account',
                'om_account_accountant',
                'product',
                'account_statement_base'
                ],
    'data': [
            'security/ir.model.access.csv',
            'security/security_view.xml',
            'data/account_journal_data.xml',
            'data/cash_move_type_data.xml',
            'data/sequence_data.xml',
            'wizard/account_currency_equalization_view.xml',
            'wizard/generate_opening_entries.xml',
            'report/account_invoice_report_view.xml',
            'report/invoice_percentage.xml',
            'report/payment_consensus_report.xml',
            'views/account_journal_inherit_view.xml',
            'views/partner_type_register_view.xml',
            'views/cash_move_type_view.xml',
            'views/account_move_inherit_view.xml',
            'views/report_view.xml',
            'views/account_res_bank_view.xml',
            'views/res_partner_inherit_view.xml',
            'views/res_company_inherit_view.xml',
            'views/product_product_inherit_view.xml',
            'views/account_account_inherit_view.xml',
            'views/account_bank_statement_line_view.xml',
            'views/res_partner_bank_inherit_view.xml',
            'views/bank_statement_line_form_reconcile_inherit_view.xml',
            'views/account_move_line_search_view.xml',
            
            'views/menu_view.xml',
            

    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
