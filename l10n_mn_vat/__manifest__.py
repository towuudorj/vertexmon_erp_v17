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
    "name" : "Mongolian Vat",
    "version" : "1.0",
    "author" : "AIBI Development Team",
    "category" : "Account",
    "license": "AGPL-3",
    'website': 'www.aibi.mn',
    "description": """
        Mongolian ebarimt system integration 3.0
    """,
    "depends" : [
                 'account',
                 'base',
                 'l10n_mn_account',
                 'stock',
                 'product'
                 ],
    "data" : [
                "data/data_auto_send_cron.xml",
                "data/product_category_data_five.xml",
                "data/product_category_data_four.xml",
                "data/product_category_data_six.xml",
                "data/product_category_data_three.xml",
                "data/product_category_data_two.xml",
                "data/product_category_data.xml",
                "data/vat_configure_data.xml",
                "security/security_view.xml",
                "security/ir.model.access.csv",
                "wizard/action_create_vat_send_view.xml",
                "wizard/action_create_vat_invoice_view.xml",
                "views/product_inherit_view.xml",
                "views/res_company_inherit_view.xml",
                "views/res_partner_inherit_view.xml",
                "views/account_move_inherit_view.xml",
                "views/vat_configure_view.xml",
                "views/vat_data_view.xml",
                "views/vat_district_view.xml",
                "views/vat_category_view.xml",
                "views/menu_view.xml"
                ],
    "auto_install": False,
    "installable": True,
}