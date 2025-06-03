# -*- coding: utf-8 -*-

import xlrd, base64, xlwt
from io import StringIO
from odoo import api, fields, models


class ndsh_seven_a_report(models.TransientModel):
    _inherit = 'abstract.report.excel'
    _name = 'ndsh.seven.a.report'