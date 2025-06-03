# -*- coding: utf-8 -*-
# Code of Margad-Erdene.S outsourcing developer

{
    'name': 'Currency downloader cron',
    'version': '1.1',
    'category': 'Accounting/Accounting',
    'sequence': 902,
    'summary': 'Download currency rate from Bank of Mongolia',
    'description': "",
    'website': 'http://www.aibi.mn',
    'depends': ['base'],
    'data': [
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': True,
}
