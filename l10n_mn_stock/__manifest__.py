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
    "version" : "1.1",
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
                 'sale_stock',
                 'purchase_stock',
                 'stock_delivery',
                 'stock_landed_costs',
                 'l10n_mn_account',
                 'l10n_mn_purchase',
                 'vertexmon_tools',
                 'rt_product_brand',
                 'hr',
                 ],
    "data" : [
                'data/sequence_data.xml',
                'security/security.xml',
                'security/ir.model.access.csv',
                'report/mn_stock_expense.xml',
                'report/mn_stock_income.xml',
                'report/mn_stock_requisition_report.xml',
                'report/mn_stock_requisition_desc.xml',
                'report/stock_requisition_template_report_view.xml',
                'report/stock_expense_template_report_view.xml',
                'report/stock_income_template_report_view.xml',
                'report/stock_workwear_template_report_view.xml',
                'report/mn_device_handing_act.xml',
                'report/mn_stock_expense_desc.xml',
                'report/mn_stock_expense_picked.xml',
                'report/purchase_add_expense_report.xml',
                'report/product_quantity_page_view.xml',
                'report/purchase_product_income_report_view.xml',
                'report/ot_packing_list_report.xml',
                'report/workwear_report.xml',
                'wizard/product_detail_report.xml',
                'wizard/product_summary_report.xml',
                'wizard/supply_product_report.xml',
                'wizard/supply_writeoff_wizard.xml',
                'wizard/product_aged_report_view.xml',
                'wizard/product_sales_report_view.xml',
                'wizard/stock_move_update_wizard.xml',
                'wizard/stock_warehouse_flow_report.xml',
                'views/distributor_register_view.xml',
                'views/product_inherit_view.xml',
                'views/item_group_view.xml',
                'views/product_category_new_view.xml',
                'views/stock_picking_inherit_view.xml',
                'views/stock_quant_inherit_view.xml',
                'views/stock_move_line_inherit_view.xml',
                'views/stock_location_view.xml',
                'views/supply_employee_balance_view.xml',
                'data/supply_writeoff_data.xml',
                'data/supply_writeoff_cron.xml',
                'report/product_require_report_view.xml',
                'report/mn_ot_purchase_receipt_report.xml',
                'views/menu_view.xml',
                'views/report_view.xml',
                'views/stock_picking_pending_view.xml',
                ],
    'assets': {
        'web.assets_backend': [
            'l10n_mn_stock/static/src/css/*.css'
        ]
    },
    "auto_install": False,
    "installable": True,
}
