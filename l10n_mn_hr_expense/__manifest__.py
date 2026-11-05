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
    'name': 'Mongolian HR Expense',
    'version': '1.0',
    'category': 'hr',
    'sequence': 35,
    'author': 'AIBI Developer Team',
    'license': 'AGPL-3',
    'summary': 'Human resource additional development',
    'description': """Mongolian hr expense additional module""",
    'website': 'www.aibi.mn',
    'depends': [
                 'base',
                 'hr',
                 'account',
                 'hr_expense',
                 'vertexmon_tools',
                ],
    'data': [
            'data/cron_data.xml',
            'report/expense_report_view.xml',
            'views/hr_expense_sheet_inherit_view.xml',
            'views/report_view.xml',
            'views/menu_view.xml',
    ],
    'assets':
        {
            'web.assets_backend': [
            ],
        },
    'installable': True,
    'application': False,
    'auto_install': False,
}
