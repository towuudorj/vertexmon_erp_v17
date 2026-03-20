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
    "name" : "Mongolian Landed Cost",
    "version" : "1.0",
    "author" : "AIBI Development Team",
    "category" : "Account",
    "license": "AGPL-3",
    'website': 'www.aibi.mn',
    "description": """
        Mongolian landed cost module
    """,
    "depends" : [
                 'account',
                 'base',
                 'l10n_mn_account',
                 'stock',
                 'product',
                 'stock_landed_costs',
                 'stock_account'
                 ],
    "data" : [
                "views/stock_landed_cost_inherit_view.xml",
                "views/account_move_inherit_view.xml",
                ],
    "auto_install": False,
    "installable": True,
}