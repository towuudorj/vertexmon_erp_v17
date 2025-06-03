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
    "name" : "Mongolian QPay",
    "version" : "1.0",
    "author" : "AIBI Development Team",
    "category" : "Account",
    "license": "AGPL-3",
    'website': 'www.aibi.mn',
    "description": """

    """,
    "depends" : [
                 'account',
                 'base',
                 'l10n_mn_account',
                 ],
    "data" : [ 
                "security/security_view.xml",
                "security/ir.model.access.csv",
                "views/qpay_configure_view.xml",
                "views/account_move_inherit.xml",
                "views/menu_view.xml",
                ],
    "auto_install": False,
    "installable": True,
}