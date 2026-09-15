# -*- coding: utf-8 -*-
{
    "name": "Mongolian Product Archive Check",
    "version": "1.3",
    "author": "AIBI Development Team",
    "category": "Inventory",
    "license": "AGPL-3",
    "summary": "Бараа архивлахын өмнө үлдэгдэл болон ноорог төлөвтэй баримтуудад ашиглагдаж буй эсэхийг шалгана",
    "depends": [
        "l10n_mn_project",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_archive_check_view.xml",
        "views/product_dead_stock_report_view.xml",
        "views/product_merge_reassign_log_view.xml",
        "wizard/product_merge_reassign_wizard_view.xml",
    ],
    "installable": True,
    "auto_install": False,
}
