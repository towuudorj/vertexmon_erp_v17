# -*- coding: utf-8 -*-
#############################################################################
#   Төслийн дугаарлалт
#    
#############################################################################
import json
from odoo import api, fields, models, _


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    
    project_id = fields.Many2one('project.project', string="Project", )
    type = fields.Selection([('inner', 'Inner'),
        ('foreign', 'Foreign'),], string='Type')


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], required=False)
