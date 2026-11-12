# -*- coding: utf-8 -*-

from odoo import fields, models


class GeneralBookReport(models.TransientModel):
    """
        Ерөнхий дэвтэр тайлан
    """
    _name = "general.book.report"
    _inherit = ['general.report.mixin']
    _description = "General book report"
    _report_title = 'Ерөнхий дэвтэр'
    _date_fields = ('date_from', 'date_to')

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    date_from = fields.Date(string="Start date", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="End date", required=True, default=fields.Date.context_today)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')
    account_ids = fields.Many2many('account.account', 'general_book_report_rel', 'account_id', 'general_id',
                                   string='Account', required=True)

    def _write_report(self, workbook, fmt):
        self._write_book_report(workbook, fmt)
