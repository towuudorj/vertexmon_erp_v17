# -*- coding: utf-8 -*-

from odoo import api, fields, models

class CreatePurchaseRequest(models.TransientModel):
    _name = 'create.purchase.request'
    _description = 'Create purchase request'


    def create_request(self):
        line_ids = self.env['crm.lead.line'].browse(self._context.get('active_ids', []))
        for line in line_ids:
            line.lead_id.create_purchase_requisition()