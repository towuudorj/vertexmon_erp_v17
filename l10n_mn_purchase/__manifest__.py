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
    "version" : "1.1",
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
                 'purchase_stock',
                 'l10n_mn_account',
                 'purchase_requisition'
                 ],
    "data" : [
              "security/ir.model.access.csv",
              "report/mn_purchase_receipt.xml",
              "report/eng_purchase_receipt.xml",
              "report/purchase_order_templates.xml",
              "report/purchase_quotation_templates.xml",
              "wizard/create_invoice_from_purchase_wizard.xml",
              "views/purchase_order_inherit_view.xml",
              "views/purchase_requisition_inherit_view.xml",
              "views/freight_type_register_view.xml",
              "wizard/purchase_summary_report_view.xml",
              "views/report_view.xml",
              "wizard/purchase_expense_report_view.xml",
              "wizard/purchase_order_template_report_view.xml",
              "views/menu_view.xml",
              "views/purchase_order_action_list_view.xml"
                ],
    "auto_install": False,
    "installable": True,
}