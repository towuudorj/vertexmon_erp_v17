# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderCancel(models.TransientModel):
    _inherit = 'sale.order.cancel'

    cancel_reason = fields.Char(string='Cancel Reason', required=True)



    def action_cancel(self):
        for line in self:
            line.order_id.cancel_reason = line.cancel_reason
        return self.order_id.with_context(disable_cancel_warning=True).action_cancel()
    
    def action_send_mail_and_cancel(self):
        self.ensure_one()
        self.order_id.message_post(
            author_id=self.author_id.id,
            body=self.body,
            message_type='comment',
            email_layout_xmlid='mail.mail_notification_light',
            partner_ids=self.recipient_ids.ids,
            subject=self.subject,
        )
        for line in self:
            line.order_id.cancel_reason = line.cancel_reason
        return self.action_cancel()