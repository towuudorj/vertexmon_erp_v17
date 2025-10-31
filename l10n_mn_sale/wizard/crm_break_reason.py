# -*- coding: utf-8 -*-

from odoo import api, fields, models

class CrmBreakReason(models.TransientModel):
    _name = 'crm.break.reason'
    _description = 'Crm break reason'

    reason = fields.Text(string='Break reason', required=True)

    def action_break_reason(self):
        line_ids = self.env['crm.lead'].browse(self._context.get('active_ids', []))
        for line in line_ids:
            line.break_reason = self.reason
            line.new_status = 'break'