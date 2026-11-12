# -*- coding: utf-8 -*-

from odoo import fields, models


class GeneralBookReportTwo(models.TransientModel):
    """
        Ерөнхий дэвтэр тайлан 2
    """
    _name = "general.book.report.two"
    _inherit = ['general.report.mixin']
    _description = "General book report 2"
    _report_title = 'Ерөнхий дэвтэр 2'
    _date_fields = ('date_start', 'date_end')

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    date_start = fields.Date(string="Start date", required=True, default=fields.Date.context_today)
    date_end = fields.Date(string="End date", required=True, default=fields.Date.context_today)
    is_sales = fields.Boolean(string='Sales', default=False)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')
    account_ids = fields.Many2many('account.account', 'general_book_report_two_rel', 'account_id', 'general_id',
                                   string='Account', required=True)

    def _write_report(self, workbook, fmt):
        self._write_book_report(workbook, fmt)
