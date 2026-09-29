# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    project_budget_monitor = fields.Boolean(string='Төслийн төсөв хянах')
