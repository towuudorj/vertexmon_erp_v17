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
    "name" : "Mongolian Stock",
    "version" : "1.0",
    "author" : "AIBI Development Team",
    "category" : "Account",
    "license": "AGPL-3",
    "website": 'www.aibi.mn',
    "description": """

    """,
    "depends" : [
                 'product',
                 'base',
                 'stock',
                 'stock_delivery'
                 ],
    "data" : [
                'security/ir.model.access.csv',
                'report/mn_stock_expense.xml',
                'report/mn_stock_income.xml',
                'report/mn_stock_requisition_report.xml',
                'report/mn_device_handing_act.xml',
                'report/mn_stock_expense_desc.xml',
                'views/distributor_register_view.xml',
                'views/product_inherit_view.xml',
                'views/item_group_view.xml',
                'views/product_category_new_view.xml',
                'views/stock_picking_inherit_view.xml',
                'views/stock_quant_inherit_view.xml',
                'views/menu_view.xml',
                'views/report_view.xml',
                ],
    "auto_install": False,
    "installable": True,
}