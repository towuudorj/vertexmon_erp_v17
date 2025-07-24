# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from xlwt import Workbook, Formula

class MultiCompanyProfitExcelReport(models.TransientModel):
    """
        Татварын албанд зориулсан Орлогын тайлан
    """
    _name = "multi.company.profit.excel.report"
    _description = "Tax Department"
    
    company_id=fields.Many2one('res.company', string='Company', required=True,
                               default=lambda self: self.env.user.company_id)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year',required=True)
    date_from=fields.Date("Start Date", required=True,default=fields.Date.context_today)
    date_to=fields.Date("End Date", required=True,default=fields.Date.context_today)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries'),
                                    ], string='State', required=True, default='posted')


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'target_move': self.target_move
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'multi.company.profit.excel.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account profit multi company report'}
        }         