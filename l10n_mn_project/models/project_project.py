# -*- coding: utf-8 -*-
#############################################################################
#   Төслийн дугаарлалт
#    
#############################################################################
import json
from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.depends('products_line.price_total')
    def _amount_all(self):
        for order in self:  
            total_amount = 0
            total_tax_amount = 0
            total_cost = 0
            for line in order.products_line:
                total_amount += line.price_total
                total_tax_amount += (line.price_total/100.0)*10.0
                total_cost += line.cost_total
            order.update({
                'total_amount': total_amount+total_tax_amount,
                'total_tax_amount':total_tax_amount,
                'untax_amount':total_amount,
                'total_cost':total_cost
            })
    
    def _get_crm_count(self):
        crm_obj = self.env['crm.lead']
        for line in self:
            count = 0
            crm_id = crm_obj.search([('id','in',line.crm_ids.ids)])
            if crm_id:
                for crm in crm_id:
                    count +=1
            line.crm_count = count
            

    sequence_name = fields.Char("Sequence", copy=False)
    contract_number = fields.Char(string='Contract Number', copy=False)
    contract_amount = fields.Float(string='Contract Amount', digits='Product Price')
    products_line = fields.One2many('project.products.line', 'project_id', string='Products Line', copy=True,)
    total_amount = fields.Monetary(string='Total Amount', store=True, readonly=True, compute='_amount_all')
    untax_amount = fields.Monetary(string='Untax Amount', store=True, readonly=True, compute='_amount_all')
    total_tax_amount = fields.Monetary(
        string='Total Tax Amount', store=True, readonly=True, compute='_amount_all'
    )
    total_cost = fields.Monetary(
        string='Total Cost', store=True, readonly=True, compute='_amount_all'
    )
    product_notes = fields.Char('Product Notes')
    project_type = fields.Selection([
        ('project', 'Project'),
        ('tender', 'Tender'),
    ], string='Type', default='project')
    purchase_requisition_count = fields.Integer(
        compute="_compute_purchase_requisition", string="# Purchase requisition"
    )
    purchase_ids = fields.Many2many('purchase.order', string='Purchase order')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    picking_type_id = fields.Many2one('stock.picking.type', string='Stock picking type')
    purchase_manager_id = fields.Many2one('res.users', string='Purchase Manager',)
    crm_count = fields.Integer(string='Crm count', compute="_get_crm_count")
    crm_ids = fields.Many2many('crm.lead', string='Crm ids')
    picking_ids = fields.Many2many('stock.picking', string='Picking')
    picking_count = fields.Integer(string='Picking count', compute="action_picking_count")
    
    
    def action_picking_count(self):
        for line in self:
            count = 0
            if line.picking_ids:
                for li in line.picking_ids:
                    count +=1
            line.picking_count = count
    
    
    def action_view_picking(self, picking=False):
        if not picking:
            picking = self.mapped('picking_ids')
        action = self.env['ir.actions.actions']._for_xml_id('stock.action_picking_tree_all')
        if len(picking) > 1:
            action['domain'] = [('id', 'in', picking.ids)]
        elif len(picking) == 1:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = picking.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action
    
    def action_view_crm_lead(self, purchases=False):
        if not purchases:
            purchases = self.mapped('crm_ids')
        action = self.env['ir.actions.actions']._for_xml_id('crm.crm_lead_opportunities')
        if len(purchases) > 1:
            action['domain'] = [('id', 'in', purchases.ids)]
        elif len(purchases) == 1:
            form_view = [(self.env.ref('crm.crm_lead_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = purchases.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action
    
    
    def action_view_purchase_requisition(self, purchases=False):
        if not purchases:
            purchases = self.mapped('purchase_ids')
        action = self.env['ir.actions.actions']._for_xml_id('purchase.purchase_rfq')
        if len(purchases) > 1:
            action['domain'] = [('id', 'in', purchases.ids)]
        elif len(purchases) == 1:
            form_view = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = purchases.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    @api.model_create_multi
    def create(self,vals_list):
        for vals in vals_list:
            if vals.get('sequence_name', _('New')) == _('New'):
                vals['sequence_name'] = self.env['ir.sequence'].next_by_code('project.project') or _('New')
        return super(ProjectProject, self).create(vals_list)
    
    
    #### Худалдан авалтын хүсэлт үүгэх
    def action_create_purchase_requisition(self):
        
        foreign_line = self.env['project.products.line'].search([('is_purchase','=', False),('project_id','=', self.id)])
        # for line in self.products_line:
        if foreign_line:
            for_req_id = self.env['purchase.requisition'].create({
                'user_id': self.user_id.id,
                'date_end':self.date,
                'schedule_date':self.date,
                'origin': self.name,
                'project_id': self.id,
                'description':self.description,
                'type': 'foreign',
            })  
        inner_line = self.env['project.products.line'].search([('is_purchase','=', False),('project_id','=', self.id)])
          
        if inner_line:
            requisition_id = self.env['purchase.requisition'].create({
                'user_id': self.user_id.id,
                'date_end':self.date,
                'schedule_date':self.date,
                'origin': self.name,
                'project_id': self.id,
                'description':self.description,
                'type': 'inner'
            })
        for line in self.products_line:
            if line.is_purchase == False:
                if line.product_qty > line.qty_available:
                    if line.is_foreign_purchases:
                        if line.product_id:
                            vals={
                                'product_id': line.product_id.id,
                                'product_description_variants': line.name,
                                'product_qty':line.product_qty,
                                'requisition_id': for_req_id.id,

                            }
                        else:
                            vals={
                                'product_description_variants': line.name,
                                'product_qty':line.product_qty,
                                'requisition_id': for_req_id.id,

                            }
                    else:
                        if line.product_id:
                            vals={
                                'product_id': line.product_id.id,
                                'product_description_variants': line.name,
                                'product_qty':line.product_qty,
                                'requisition_id': requisition_id.id,

                            }
                        else:
                            vals={
                                'product_description_variants': line.name,
                                'product_qty':line.product_qty,
                                'requisition_id': requisition_id.id,

                            }
                
                    self.env['purchase.requisition.line'].create(vals)
                    line.write({'is_purchase': True})
        return True
        
     #### Даалгавар үүсгэх
    def action_create_tasks(self):
        line_ids = []
        view = self.env.ref('l10n_mn_project.view_project_pack_tasks')
        for line in self.products_line:
            qty = 0 
            if line.product_qty > 0.0 and line.qty_delivered:
                if line.product_qty > line.qty_delivered:
                    qty = line.product_qty - line.qty_delivered
                else:
                    qty = 0
            else:
                qty = line.product_qty
            pline_vals ={
                'product_id': line.product_id.id,
                'quantity': qty,
                'pline_id': line.id,
                'project_id': self.id
            }
            lines = self.env['project.package.task.create.line'].create(pline_vals)
            line_ids.append(lines.id)
        wiz = self.env['project.package.task.create'].create({
            'product_lines': line_ids,
                                                       })
        # TDE FIXME: a return in a loop, what a good idea. Really.
        return {
            'name': _('Create Packege Task'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.package.task.create',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': self.env.context,
        }

    #### Даалгавар үүсгэх
    # def action_create_tasks(self):

    #     for line in self.products_line:
    #         if line.is_task == False:
    #             vals={
    #                 'project_id': self.id,
    #                 'name':line.name,
    #                 'date_deadline': self.date
    #             }
    #             task = self.env['project.task'].create(vals)
    #             line_vals = {
    #                 'product_id': line.product_id.id,
    #                 'name': line.name,
    #                 'product_qty':line.product_qty,
    #                 'price_unit': line.price_unit,
    #                 'task_id': task.id,
    #             }
    #             self.env['task.products.line'].create(line_vals)
    #             line.write({'is_task': True})
            
                # ###### Агуулахын хөдөлгөөн үүсгэх
                # if self.warehouse_id.delivery_steps == 'pick_ship':
                #     pick_val = {
                #         'partner_id': self.partner_id.id,
                #         'picking_type_id': self.warehouse_id.pick_type_id.id,
                #         'scheduled_date':self.date,
                #         'origin': task.name,
                #         'task_id': task.id,
                #         'location_id': self.warehouse_id.lot_stock_id.id,
                #     }
                #     out_val ={
                #         'partner_id': self.partner_id.id,
                #         'picking_type_id': self.warehouse_id.out_type_id.id,
                #         'scheduled_date':self.date,
                #         'origin': task.name,
                #         'task_id': task.id,
                #         'location_id': self.warehouse_id.wh_output_stock_loc_id.id,
                #     }
                #     if line.product_id:
                #         picking = self.env['stock.picking'].create(pick_val)
                #         out_picking = self.env['stock.picking'].create(out_val)
                #         move_vals = {
                #             'product_id': line.product_id.id,
                #             'date': self.date,
                #             'name': line.name,
                #             'product_uom_qty': line.product_qty,
                #             'product_uom': line.product_id.uom_id.id,
                #             'picking_id': picking.id,
                #             'location_id': self.warehouse_id.lot_stock_id.id,
                #             'location_dest_id':self.warehouse_id.wh_output_stock_loc_id.id,
                #         }

                #         move = self.env['stock.move'].create(move_vals)
                #         picking.action_confirm()

                #         customer_loc = self.env['stock.location'].search([('usage', '=', 'customer')])
                #         out_move_vals = {
                #             'product_id': line.product_id.id,
                #             'date': self.date,
                #             'name': line.name,
                #             'product_uom_qty': line.product_qty,
                #             'product_uom': line.product_id.uom_id.id,
                #             'picking_id': out_picking.id,
                #             'location_id': self.warehouse_id.wh_output_stock_loc_id.id,
                #             'location_dest_id':customer_loc[0].id,
                #         }

                #         move = self.env['stock.move'].create(out_move_vals)
                #         out_picking.action_confirm()
                # else:
                #     pick_val = {
                #         'partner_id': self.partner_id.id,
                #         'picking_type_id': self.warehouse_id.pick_type_id.id,
                #         'scheduled_date':self.date,
                #         'origin': task.name,
                #         'task_id': task.id,
                #         'location_id': self.warehouse_id.lot_stock_id.id,
                #     }
                #     if line.product_id:
                #         picking = self.env['stock.picking'].create(pick_val)
                #         customer_loc = self.env['stock.location'].search([('usage', '=', 'customer')])
                #         out_move_vals = {
                #             'product_id': line.product_id.id,
                #             'date': self.date,
                #             'name': line.name,
                #             'product_uom_qty': line.product_qty,
                #             'product_uom': line.product_id.uom_id.id,
                #             'picking_id': picking.id,
                #             'location_id': self.warehouse_id.wh_output_stock_loc_id.id,
                #             'location_dest_id':customer_loc[0].id,
                #         }

                #         move = self.env['stock.move'].create(out_move_vals)
                #         picking.action_confirm()


    def _compute_purchase_requisition(self):
         for project in self:
            groups = self.env["purchase.order"].search([('id', 'in', project.purchase_ids.ids ),('state','!=','cancel')])
            # purchase_line_total = 0
            # for group in groups:
            #     purchase_line_total += group["price_subtotal"]
            project.purchase_requisition_count = len(groups)
            # project.purchase_line_total = purchase_line_total
    
    def  _domain_purchase_requisition(self):   
        domain = [('project_id', '=', self.id )]
        return domain

    def button_open_purchase_requisition(self):
        self.ensure_one()
        return {
            "name": _("Purchase requisition"),
            "domain": self._domain_purchase_requisition(),
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "purchase.requisition",
        }