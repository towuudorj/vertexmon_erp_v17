# -*- coding: utf-8 -*-
#################################################################################
# Author      : Zero For Information Systems (<www.erpzero.com>)
# Copyright(c): 2016-Zero For Information Systems
# All Rights Reserved.
#zerosystems #erp #odoo
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    'name': 'Stock Effective Date |Inventory Backdate',
    'version': '7.0.1',
    'category': 'Warehouse',
    "author": 'Zero Systems',
    "company": 'Zero for Information Systems',
    "website": "https://www.erpzero.com",
    "email": "sales@erpzero.com",
    'live_test_url': 'https://youtu.be/K8E7lvd9OxM',
    "sequence": 0,
    'summary': """
        Stock Editable & Visible and default equal Scheduled Date on the picking, stock move & the journal.""",
    'description': """
        Stock Editable & Visible and default equal Scheduled Date on the picking, stock move & the journal.
        Stock accounting Date,warehouse Effective Date, stock picking actual date, stock transfer actual date
        Force date in Stock Transfer,stock_date,stock date
        Change Effective Date on Stock App
        Odoo Stock Change Effective Date App
        Change effective date in transfer -stock picking
        User can change effective date in transfer and also change date in stock move and change date it related inventory valuation 
        and journal.

    """,
    'depends': ['stock_account'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'license': 'OPL-1',
    'images': ['static/description/stock_effictive_date.JPG'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'price': 15.0,
    'currency': 'EUR',
    'pre_init_hook': 'pre_init_check',
}
