# -*- coding: utf-8 -*-

from odoo import api, fields, models

class CrmCancelReason(models.TransientModel):
    _name = 'crm.cancel.reason'
    _description = 'Crm cancel reason'

    reason = fields.Text(string='Cancel reason', required=True)

    def action_cancel_reason(self):
        line_ids = self.env['crm.lead'].browse(self._context.get('active_ids', []))
        for line in line_ids:
            line.cancel_reason = self.reason
            line.new_status = 'cancel'
            for lines in line.lead_line_ids:
                lines.state = 'cancel'