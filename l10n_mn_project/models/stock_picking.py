# -*- coding: utf-8 -*-
#############################################################################
#   Төслийн дугаарлалт
#    
#############################################################################
import json
from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    task_id = fields.Many2one('project.task', string='Project Task')


class StockMove(models.Model):
    _inherit = 'stock.move'

    project_balance = fields.Integer('Project Balance', compute='_compute_project_balance')
    product_in_project = fields.Boolean('Product In Project', compute='_compute_project_balance')


    def _compute_project_balance(self):
        for obj in self:
             if obj.picking_id.analytic_id.project_ids:
                 project = obj.picking_id.analytic_id.project_ids[0]
                 project_line = project.products_line.filtered(lambda line: line.product_id.id == obj.product_id.id)
                 if project_line:
                     obj.product_in_project = True
                     obj.project_balance = project_line[0].last_qty
                 else:
                     obj.product_in_project = False
                     obj.project_balance = 0
             else:
                 obj.product_in_project = False
                 obj.project_balance = 0