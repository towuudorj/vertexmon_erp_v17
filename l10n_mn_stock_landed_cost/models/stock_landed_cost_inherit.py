# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import json, requests

class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    po_ids = fields.Many2many('purchase.order', string=u'Худалдан авалт', domain="[('state','=','purchase')]")
    picking_ids = fields.Many2many(
        'stock.picking', string=u'Орлогын баримт',
        copy=False)

    
    #def _compute_picking_ids(self):
    #    for rec in self:
    #        for po in rec.po_ids:
    #            if po.picking_ids:
    #                for picking in po.picking_ids:
    #                    if picking.state in ['done']:
    #                        rec.picking_ids |= picking


class StockValuationAdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    unit_price =  fields.Float(string=u'Шингэсэн нэгж өртөг', compute="_compute_unit_price")

    @api.depends('final_cost','quantity')
    def _compute_unit_price(self):
        for line in self:
            if line.quantity >0.0:
                unit_cost = line.final_cost/line.quantity
            line.unit_price = unit_cost





    

 


