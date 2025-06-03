# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'



    def print_line_report(self):
        if self.journal_id.type == 'bank':
            return self.env.ref('l10n_mn_account_report.payment_order_report_data_new_pdf').report_action(self)
        else:
            return self.env.ref('l10n_mn_account_report.cash_order_report').report_action(self)

    def print_line_report_transport(self):
        return self.env.ref('l10n_mn_account_report.payment_order_transport_report_data').report_action(self)

