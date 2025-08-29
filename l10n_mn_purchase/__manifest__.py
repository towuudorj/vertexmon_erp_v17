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
    "name" : "Mongolian Purchase",
    "version" : "1.0",
    "author" : "AIBI Development Team",
    "category" : "Account",
    "license": "AGPL-3",
    'website': 'www.aibi.mn',
    "description": """
        Mongolian purchase module
    """,
    "depends" : [
                 'product',
                 'base',
                 'purchase',
                 'l10n_mn_account',
                 'purchase_requisition'
                 ],
    "data" : [
              "security/ir.model.access.csv",
              "report/mn_purchase_receipt.xml",
              "report/eng_purchase_receipt.xml",
              "views/purchase_order_inherit_view.xml",
              "views/purchase_requisition_inherit_view.xml",
              "views/freight_type_register_view.xml",
              "views/report_view.xml",
              "wizard/purchase_expense_report_view.xml",
              "views/menu_view.xml"
                ],
    "auto_install": False,
    "installable": True,
}