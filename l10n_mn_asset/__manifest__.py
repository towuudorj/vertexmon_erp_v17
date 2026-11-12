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
    'name': 'Mongolian Asset',
    'version': '1.1',
    'category': 'Accounting',
    'sequence': 35,
    'author': 'AIBI Developer Team',
    'license': 'AGPL-3',
    'summary': 'Financial and Analytic Accounting',
    'description': """Mongolian asset additional module""",
    'website': 'www.aibi.mn',
    'depends': [
                'om_account_asset',
                'account',
                'analytic',
                'purchase',
                'om_account_accountant',
                'hr',
                'stock',
                'l10n_mn_account',
                'l10n_mn_account_report',
                'l10n_mn_stock',
                ],
    'data': [
            'data/account_journal_data.xml',
            'data/account_account_data.xml',
            'data/account_asset_category_data.xml',
            'data/stock_location_data.xml',
            'security/ir.model.access.csv',
            'wizard/asset_capitalization_view.xml',
            'wizard/account_asset_writeoff_view.xml',
            'wizard/account_asset_detail_report_view.xml',
            'wizard/stock_to_asset_wizard_view.xml',
            'wizard/asset_sale_view.xml',
            'wizard/asset_category_transfer_view.xml',
            'wizard/account_asset_gl_reconcile_view.xml',
            'wizard/asset_rename_view.xml',
            'views/mn_asset_inherit.xml',
            'views/account_asset_category_view.xml',
            'views/asset_location_view.xml',
            'report/asset_move_report.xml',
            'views/account_asset_move_view.xml',
            'views/asset_list_column_filter_view.xml',
            'absract_report_view.xml',
            'views/report_view.xml',
            'report/asset_owner_card_report.xml',
            'views/menu_view.xml',


    ],
    'assets': {
        'web.assets_backend': [
            'l10n_mn_asset/static/src/scss/asset_form.scss',
        ],
    },
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
