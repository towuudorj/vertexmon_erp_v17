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
    "name" : "Mongolian Project",
    "version" : "17.0.0.1",
    "author" : "AIBI Development Team",
    "category" : "Project",
    "license": "AGPL-3",
    'website': 'www.aibi.mn',
    "description": """
        Mongolian project development module
    """,
    "depends" : [
                 'project',
                 'sale_project',  # invoice_count-ийн эрхийг дарж бичихийн тулд түүний дараа ачаалагдана
                 'base',
                 'stock',
                 'purchase_requisition',
                 'purchase',
                 'purchase_stock',
                 'l10n_mn_sale',
                 'l10n_mn_account',
                 'l10n_mn_purchase'
                 ],
    "data" : [ 
            'security/ir.model.access.csv',
            'security/security_view.xml',
            'data/ir_sequence_data.xml',
            'data/rule.xml',
            'data/project_task_type_data.xml',
            'wizard/foreign_purchase_request_wizard.xml',
            'wizard/local_purchase_request_wizard.xml',
            'wizard/make_package_task_wizard.xml',
            'wizard/project_invoice_wizard.xml',
            'views/project_project_views.xml',
            'views/project_task_view.xml',
            'views/crm_lead_view.xml',
            'views/purchase_requisition_view.xml',
            'views/stock_picking_view.xml',
            'views/invoice_view_inherit.xml',
            'views/product_category_view.xml',
            'views/product_template_view.xml',
            'views/menu_view.xml',

                ],
    "assets": {
        "web.assets_backend": [
            "l10n_mn_project/static/src/js/project_planned_qty_field.js",
        ],
    },
    "auto_install": False,
    "installable": True,
}