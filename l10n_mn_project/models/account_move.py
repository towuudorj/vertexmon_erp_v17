# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        for move in posted.filtered(lambda m: m.move_type == 'in_invoice'):
            orders = move.invoice_line_ids.purchase_line_id.order_id
            projects = orders.analytic_id.project_ids
            products = move.invoice_line_ids.product_id
            for project in projects:
                lines = project.products_line.filtered(lambda l: l.product_id in products)
                lines._check_budget_threshold()
        return posted
