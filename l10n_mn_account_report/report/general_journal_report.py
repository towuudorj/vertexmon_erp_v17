# -*- coding: utf-8 -*-

from odoo import fields, models


class GeneralJournalReport(models.TransientModel):
    """
        Ерөнхий журнал тайлан
    """
    _name = "general.journal.report"
    _inherit = ['general.report.mixin']
    _description = "General journal report"
    _report_title = 'Ерөнхий журнал'
    _date_fields = ('date_from', 'date_to')

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    date_from = fields.Date(string="Start date", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="End date", required=True, default=fields.Date.context_today)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')
    account_ids = fields.Many2many('account.account', 'general_journal_report_rel', 'account_id', 'general_id',
                                   string='Account', required=True)

    def _write_report(self, workbook, fmt):
        self._write_journal_report(workbook, fmt, with_balance=False)
