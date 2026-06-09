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
                 'base',
                 'stock',
                 'purchase_requisition',
                 'purchase',
                 'l10n_mn_sale',
                 'l10n_mn_account'
                 ],
    "data" : [ 
            'security/ir.model.access.csv',
            'security/security_view.xml',
            'data/ir_sequence_data.xml',
            'wizard/foreign_purchase_request_wizard.xml',
            'wizard/local_purchase_request_wizard.xml',
            'wizard/make_package_task_wizard.xml',
            'wizard/project_invoice_wizard.xml',
            'views/project_project_views.xml',
            'views/project_task_view.xml',
            'views/purchase_requisition_view.xml',
            'views/stock_picking_view.xml',

                ],
    "auto_install": False,
    "installable": True,
}