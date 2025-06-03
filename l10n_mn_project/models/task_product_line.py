# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from itertools import groupby
from pytz import timezone, UTC
from werkzeug.urls import url_encode

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.tools.float_utils import float_round


class TaskProductsLine(models.Model):
    _name = "task.products.line"
    _description = "Project Product Line"
    _order = 'task_id,id'
    
    
    task_id = fields.Many2one('project.task', string='Task', index=True, required=True, ondelete='cascade')
    
    sequence = fields.Integer(string='Sequence', default=1)
    product_id = fields.Many2one('product.product', string='Product', 
                    domain=[('purchase_ok', '=', True)], change_default=True)

    name = fields.Text(
        string="Description",
        store=True, readonly=False, required=True)

    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    # product_uom = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    price_unit = fields.Float(string='Price', required=True, digits='Product Price')
    
    qty_available = fields.Float(string='Available QTY', required=True, digits='Product', readonly=True, default=0)
    qty_delivered = fields.Float(string='Delivered', required=True, digits='Product', readonly=True, default=0)
   
    price_total = fields.Float(string='Total Price', store=True, readonly=True)
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    
    @api.onchange('price_unit')
    def onchange_price_unit(self):
        if self.product_qty > 0:
            self.price_total = self.price_unit * self.product_qty
            
    @api.onchange('product_qty')
    def onchange_product_qty(self):
        
        if not self.product_id:
            return
        
        self.price_total = self.price_unit * self.product_qty
        
        
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            return
        
        self.price_unit = self.product_id.list_price
        self.name = self.product_id.description
        self.qty_available = self.with_context({'to_date': datetime.today()}).qty_available
        self.price_total = self.price_unit * self.product_qty
                                    
   
    