from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _create_or_update_picking(self):
        if self.env.context.get('skip_split_purchase_picking'):
            return True
        return super()._create_or_update_picking()
