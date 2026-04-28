from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        if self.env.context.get('skip_split_stock_rule'):
            return True
        return super()._action_launch_stock_rule(previous_product_uom_qty=previous_product_uom_qty)
