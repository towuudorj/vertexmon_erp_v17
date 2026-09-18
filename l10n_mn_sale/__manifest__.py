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
    "name" : "Mongolian Sale",
    "version" : "1.1",
    "author" : "AIBI Development Team",
    "category" : "Account",
    "license": "AGPL-3",
    'website': 'www.aibi.mn',
    "description": """

    """,
    "depends" : [
                 'product',
                 'base',
                 'sale',
                 'l10n_mn_account',
                 'l10n_mn_stock',
                 'rt_product_brand',
                 'project',
                 'crm',
                 'mail',
                 'l10n_mn_account'
                 ],
    "data" : [ 
                'security/ir.model.access.csv',
                'data/sequence_data.xml',
                'data/mail_template_data.xml',
                'data/cron_data.xml',
                'security/security_view.xml',
                'report/mn_crm_invoice_not_signature.xml',
                'report/mn_crm_invoice_signature.xml',
                'report/mn_crm_invoice_percentage_signature.xml',
                'report/mn_sale_quotation.xml',
                'report/mn_sale_quotation_no_sign.xml',
                'report/mn_sale_crm_quotation_no_sign.xml',
                'report/mn_sale_crm_quotation.xml',
                'report/mn_sale_invoice.xml',
                'report/mn_sale_expense.xml',
                'report/mn_sale_expense_stamp.xml',
                'report/mn_sale_expense_desc.xml',
                'report/mn_ot_sale_invoice.xml',
                'report/sale_order_common_report_view.xml',
                'report/sale_order_new_report_view.xml',
                'report/sale_order_template_report_view.xml',
                'report/crm_quotation_template_report_view.xml',
                'report/mn_ot_stock_expense.xml',
                'wizard/create_product_wizard_view.xml',
                'wizard/create_purchase_request_wizard_view.xml',
                'wizard/sale_order_cancel_inherit_wizard.xml',
                'wizard/crm_break_reason_view.xml',
                'wizard/crm_cancel_reason_view.xml',
                'wizard/sale_order_invoice_payment_term.xml',
                'wizard/sale_make_invoice_advance_inherit.xml',
                'views/account_payment_term_line_inherit_view.xml',
                'views/account_move_inherit_view.xml',
                'views/project_project_inherit_view.xml',
                'views/crm_inherit_view.xml',
                'views/sale_order_inherit_view.xml',
                'views/res_company_inherit_view.xml',
                'views/res_users_inherit_view.xml',
                'views/sales_contract_register_view.xml',
                'views/sales_contract_type_view.xml',
                'views/purchase_requisition_inherit_view.xml',
                'views/sales_plan_register_view.xml',
                'views/purchase_reason_register_view.xml',
                'views/crm_lead_line_view.xml',
                'views/crm_team_inherit_view.xml',
                'views/report_view.xml',
                'views/menu_view.xml',
                'views/sale_order_action_list_view.xml'
                ],
    "auto_install": False,
    "installable": True,
}