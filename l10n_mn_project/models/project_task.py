# -*- coding: utf-8 -*-
#############################################################################
#   Төслийн дугаарлалт
#    
#############################################################################
import json
from odoo import api, fields, models, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # @api.depends('products_line.price_total')
    # def _amount_all(self):
    #     for order in self:  
    #         total_amount = 0
    #         for line in order.products_line:
    #             total_amount += line.price_total
    #         order.update({
    #             'total_amount': total_amount
    #         })

    products_line = fields.One2many('task.products.line', 'task_id', string='Products Line', copy=True,)
    picking_count = fields.Integer(compute="_compute_picking", string="Stock Picking")

    # total_amount = fields.Float(string='Total Amount', store=True, readonly=True, compute='_amount_all')

    # ---------------------------------------------------
    # Actions
    # ---------------------------------------------------

    # def _get_action_view_pick_ids(self):
    #     print('self=================', self)
    #     pick_ids = self.env['stock.picking'].search([('task_id', '=', self.id)])
    #     return pick_ids

    # def action_view_pick(self):
    #     pick_ids = self._get_action_view_pick_ids()
    #     action_window = {
    #         "type": "ir.actions.act_window",
    #         "res_model": "stock.picking",
    #         "name": _("Stock Picking"),
    #         "views": [[False, "tree"], [False, "form"]],
    #         "context": {"create": False},
    #         "domain": [["id", "in", pick_ids]],
    #     }
    #     if len(pick_ids) == 1:
    #         action_window["views"] = [[False, "form"]]
    #         action_window["res_id"] = pick_ids[0]

    #     return action_window

    def _compute_picking(self):
         for task in self:
            groups = self.env["stock.picking"].search([('task_id', '=', self.id )])
            # purchase_line_total = 0
            # for group in groups:
            #     purchase_line_total += group["price_subtotal"]
            task.picking_count = len(groups)
            # project.purchase_line_total = purchase_line_total
    
    def  _domain_stock_pick(self):   
        domain = [('task_id', '=', self.id )]
        return domain

    def button_open_picking(self):
        self.ensure_one()
        return {
            "name": _("Stock Picking"),
            "domain": self._domain_stock_pick(),
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "stock.picking",
        }

    def action_task_approve(self):
        picking_ids = self.create_picking()
        self.project_id.picking_ids = [(4, picking_ids.id)]
        for line in self:
            for li in line.project_id.products_line:
                for lines in line.products_line:
                    if li.product_id == lines.product_id.id:
                        li.picking_ids = [(4, picking_ids.id)]
        self.write({'state': '03_approved'})
        return True

    def create_picking(self):
        picking = False
        out_picking = False
        for lines in self:
            if self.project_id.warehouse_id.delivery_steps == 'pick_ship':
                pick_val = {
                    'partner_id': self.partner_id.id,
                    'picking_type_id': self.project_id.picking_type_id.id,
                    'scheduled_date':self.date_deadline,
                    'origin': self.name,
                    'task_id': self.id,
                    'analytic_id':self.project_id.analytic_account_id.id,
                    'location_id': self.project_id.picking_type_id.default_location_src_id.id,
                }
                out_val ={
                    'partner_id': self.partner_id.id,
                    'picking_type_id': self.project_id.picking_type_id.id,
                    'scheduled_date':self.date_deadline,
                    'origin': self.name,
                    'task_id': self.id,
                    'analytic_id':self.project_id.analytic_account_id.id,
                    'location_id': self.project_id.picking_type_id.default_location_src_id.id,
                }
                picking = self.env['stock.picking'].create(pick_val)
                out_picking = self.env['stock.picking'].create(out_val)
            else:
                pick_val = {
                            'partner_id': self.partner_id.id,
                            'picking_type_id': self.project_id.picking_type_id.id,
                            'scheduled_date':self.date_deadline,
                            'origin': self.name,
                            'task_id': self.id,
                            'analytic_id':self.project_id.analytic_account_id.id,
                            'location_id': self.project_id.picking_type_id.default_location_src_id.id,
                        }
                picking = self.env['stock.picking'].create(pick_val)
                
            for line in lines.products_line:
            ###### Агуулахын хөдөлгөөн үүсгэх
                if line.product_id:
                    if self.project_id.warehouse_id.delivery_steps == 'pick_ship':
                        move_vals = {
                            'product_id': line.product_id.id,
                            'date': self.date_deadline,
                            'name': line.name,
                            'product_uom_qty': line.product_qty,
                            'product_uom': line.product_id.uom_id.id,
                            'picking_id': picking.id,
                            'location_id': self.project_id.picking_type_id.default_location_src_id.id,
                            'location_dest_id':self.project_id.picking_type_id.default_location_dest_id.id,
                        }
    
                        move = self.env['stock.move'].create(move_vals)
                        picking.action_confirm()
    
                        customer_loc = self.env['stock.location'].search([('usage', '=', 'customer')])
                        out_move_vals = {
                            'product_id': line.product_id.id,
                            'date': self.date_deadline,
                            'name': line.name,
                            'product_uom_qty': line.product_qty,
                            'product_uom': line.product_id.uom_id.id,
                            'picking_id': out_picking.id,
                             'location_id': self.project_id.picking_type_id.default_location_src_id.id,
                            'location_dest_id':self.project_id.picking_type_id.default_location_dest_id.id,
                        }
    
                        move = self.env['stock.move'].create(out_move_vals)
                        out_picking.action_confirm()
                        
                    else:
                        
                        if line.product_id:
                            
                            customer_loc = self.env['stock.location'].search([('usage', '=', 'customer')])
                            out_move_vals = {
                                'product_id': line.product_id.id,
                                'date': self.date_deadline,
                                'name': line.name,
                                'product_uom_qty': line.product_qty,
                                'product_uom': line.product_id.uom_id.id,
                                'picking_id': picking.id,
                                 'location_id': self.project_id.picking_type_id.default_location_src_id.id,
                                 'location_dest_id':self.project_id.picking_type_id.default_location_dest_id.id,
                            }
        
                            move = self.env['stock.move'].create(out_move_vals)
                            picking.action_confirm()
        return picking
                    
                    
                    