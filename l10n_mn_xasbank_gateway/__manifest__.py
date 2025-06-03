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

    "name" : "Mongolia - Xacbank Corporate Connect",
    "version" : "1.0",
    "author" : "AIBI Developer Team",
    "category" : "account",
    "website":  "www.aibi.mn",
    "license": "AGPL-3",
    "description": """
        Mongolian XacBank System Integration module
    """,
    
    "depends" : [
                 'account',
                 'account_payment',
                 'account_statement_base',
                 'base',
                 ],
    "data" : [
                    'security/security_view.xml',
                    'security/ir.model.access.csv',
                    'views/xacbank_configure_view.xml',
                    'views/account_journal_inherit_view.xml',
                    'views/account_bank_statement_inherit_view.xml',
                    'views/menu_view.xml',
                    ],
    "auto_install": False,
    "installable": True,
}