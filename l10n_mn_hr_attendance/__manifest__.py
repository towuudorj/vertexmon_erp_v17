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
    'name': 'Mongolian Hr Attendance',
    'version': '1.0',
    'category': 'hr',
    'sequence': 35,
    'author': 'AIBI Developer Team',
    'license': 'AGPL-3',
    'summary': 'Human resource attendance additional development',
    'description': """Mongolian hr attendance additional module""",
    'website': 'www.aibi.mn',
    'depends': [
                 'base',
                 'hr',
                 'hr_attendance',
                 'resource'
                ],
    'data': [ 
            'views/hr_attendance_inherit_view.xml',
            'views/resource_calendar_inherit_view.xml',
            'views/menu_view.xml',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
