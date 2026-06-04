# -*- coding: utf-8 -*-
#############################################################################
#   Төслийн дугаарлалт
#    
#############################################################################
import json
from odoo import api, fields, models, _
import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.depends('products_line.price_total', 'products_line.cost_total', 'products_line.delivery_cost')
    def _amount_all(self):
        for order in self:
            total_amount = 0
            total_tax_amount = 0
            total_cost = 0
            for line in order.products_line:
                total_amount += line.price_total
                total_tax_amount += (line.price_total/100.0)*10.0
                if line.product_id and line.product_id.detailed_type == 'service':
                    total_cost += line.delivery_cost
                else:
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
    quality_amount = fields.Float(string='Quality Amount')
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
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse' , required=True)
    picking_type_id = fields.Many2one('stock.picking.type', string='Stock picking type', required=True)
    purchase_manager_id = fields.Many2one('res.users', string='Purchase Manager',)
    crm_count = fields.Integer(string='Crm count', compute="_get_crm_count")
    crm_ids = fields.Many2many('crm.lead', string='Crm ids')
    picking_ids = fields.Many2many('stock.picking', string='Picking')
    picking_count = fields.Integer(string='Picking count', compute="action_picking_count")
    state = fields.Selection([('planned','Planned'),
                              ('confirm','Confirm'),
                              ('process','Process'),
                              ('done','Done')],string='State', default='planned')
    product_count = fields.Integer(sttring='Product count', compute="compute_product_count")
    journal_id = fields.Many2one('account.journal',string='Journal', domain=[("type",'=',"general")])
    invoice_journal_id = fields.Many2one('account.journal', string='Journal', domain=[("type",'=',"sale")])
    close_move_id = fields.Many2one('account.move', string='Close move entry')
    invoice_id = fields.Many2one('account.move',string='Invoice')
    close_date = fields.Date(string='Close date')
    invoice_product_id = fields.Many2one('product.product',string='Invoice product', domain=[("type",'=',"service")])
    project_total_cost = fields.Monetary(string='Project Total Cost', compute='_compute_cost_profit')
    project_total_profit = fields.Monetary(string='Project Total Profit', compute='_compute_cost_profit')
    account_analytic_line_ids = fields.Many2many('account.analytic.line', string='Account analytic')
    bbo_account_id = fields.Many2one('account.account', string=u'Данс')
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    def write(self, vals):
        if vals.get('access_token'):
            self.ensure_one()  # We are not supposed to add a single access token to multiple project
            if self.privacy_visibility != 'portal':
                vals['access_token'] = ''

        # Here we modify the project's stage according to the selected company (selecting the first
        # stage in sequence that is linked to the company).
        company_id = vals.get('company_id')
        if self.env.user.has_group('project.group_project_stages') and company_id:
            projects_already_with_company = self.filtered(lambda p: p.company_id.id == company_id)
            if projects_already_with_company:
                projects_already_with_company.write({key: value for key, value in vals.items() if key != 'company_id'})
                self -= projects_already_with_company
            if company_id not in (None, *self.company_id.ids) and self.stage_id.company_id:
                ProjectStage = self.env['project.project.stage']
                vals["stage_id"] = ProjectStage.search(
                    [('company_id', 'in', (company_id, False))],
                    order=f"sequence asc, {ProjectStage._order}",
                    limit=1,
                ).id

        # directly compute is_favorite to dodge allow write access right
        if 'is_favorite' in vals:
            vals.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)

        if 'last_update_status' in vals and vals['last_update_status'] != 'to_define':
            for project in self:
                # This does not benefit from multi create, this is to allow the default description from being built.
                # This does seem ok since last_update_status should only be updated on one record at once.
                self.env['project.update'].with_context(default_project_id=project.id).create({
                    'name': _('Status Update - ') + fields.Date.today().strftime(get_lang(self.env).date_format),
                    'status': vals.get('last_update_status'),
                })
            vals.pop('last_update_status')
        if vals.get('privacy_visibility'):
            self._change_privacy_visibility(vals['privacy_visibility'])

        date_start = vals.get('date_start', True)
        date_end = vals.get('date', True)
        if not date_start or not date_end:
            vals['date_start'] = False
            vals['date'] = False
        else:
            no_current_date_begin = not all(project.date_start for project in self)
            no_current_date_end = not all(project.date for project in self)
            date_start_update = 'date_start' in vals
            date_end_update = 'date' in vals
            if (date_start_update and no_current_date_end and not date_end_update):
                del vals['date_start']
            elif (date_end_update and no_current_date_begin and not date_start_update):
                del vals['date']
        if self.state == 'process':
            if 'partner_id' in vals or 'sale_contract_id' in vals or 'user_id' in vals or 'contract_amount' in vals or 'warehouse_id' in vals or 'project_type' in vals or 'analytic_account_id' in vals:
                if not self.env.user.has_group('account.group_account_manager'):
                    raise UserError((u"Эрх бүхий ажилтан биш тул засварлах боломжгүйг анхаарна уу !"))

        res = super(ProjectProject, self).write(vals) if vals else True

        if 'allow_task_dependencies' in vals and not vals.get('allow_task_dependencies'):
            self.env['project.task'].search([('project_id', 'in', self.ids), ('state', '=', '04_waiting_normal')]).write({'state': '01_in_progress'})

        if 'active' in vals:
            # archiving/unarchiving a project does it on its tasks, too
            self.with_context(active_test=False).mapped('tasks').write({'active': vals['active']})
        if 'name' in vals and self.analytic_account_id:
            projects_read_group = self.env['project.project']._read_group(
                [('analytic_account_id', 'in', self.analytic_account_id.ids)],
                ['analytic_account_id'],
                having=[('__count', '=', 1)],
            )
            analytic_account_to_update = self.env['account.analytic.account'].browse([
                analytic_account.id for [analytic_account] in projects_read_group
            ])
            analytic_account_to_update.write({'name': self.name})
        return res
    
    def compute_product_count(self):
        for line in self:
            count = 0
            for lines in line.products_line:
                count +=1
            line.product_count = count
    
    def action_confirm(self):
        for line in self:
            line.state = 'confirm'
            
    
    def action_process(self):
        for line in self:
            line.state = 'process'
        
    def action_done(self):
        account_move_obj = self.env['account.move']
        for line in self:
            tax_ids = self.env['account.tax'].search([('company_id','=',line.company_id.id),('type_tax_use','=','sale'),('price_include','=',True)],limit=1)
            analytic_account_1 = line.analytic_account_id
            self.env.cr.execute("""
                                SELECT aml.id
                                FROM account_move_line aml
                                         LEFT JOIN account_move am on am.id = aml.move_id
                                WHERE am.move_type = 'out_invoice'
                                  and aml.analytic_distribution ? %s
                                """, [str(analytic_account_1.id)])
            invoice_line_ids = self.env['account.move.line'].browse([row[0] for row in self.env.cr.fetchall()])
            invoice_ids = invoice_line_ids.filtered(lambda aml_line: aml_line.move_id.payment_types != 'penalty')
            if invoice_ids:
                invoice_amount = line.contract_amount - sum(invoice_ids.mapped('price_unit'))
            else:
                invoice_amount = 0
            invoice_vals = {
                            'invoice_date':line.close_date,
                            'journal_id':line.invoice_journal_id.id,
                            'partner_id':line.partner_id.id,
                            'state':'draft',
                            'move_type':'out_invoice',
                            'invoice_line_ids':[],
                            'company_id':line.company_id.id,
                            'invoice_origin':'%s'%line.name
                            }
            invoice_line = {
                            'name':u'%s'%line.invoice_product_id.name,
                            'quantity':1.0,
                            'product_id':line.invoice_product_id.id,
                            'product_uom_id':line.invoice_product_id.uom_id.id,
                            'price_unit':invoice_amount,
                            'tax_ids':[(6,0,tax_ids.ids)],
                            'analytic_distribution': {
                                analytic_account_1.id: 100.0,
                            },
                            'account_id':line.invoice_journal_id.default_account_id.id,
                            }
            invoice_vals['invoice_line_ids'].append((0,0,invoice_line))
            invoice_id = account_move_obj.create(invoice_vals)


            move_value = {
                            'date':line.close_date,
                            'journal_id':line.journal_id.id,
                            'partner_id':line.partner_id.id,
                            'company_id':line.company_id.id,
                            'ref':'%s'%line.name,
                            'state':'draft',
                            'move_type':'entry',
                            'line_ids':[]
                            }

            for lines in line.products_line:
                if lines.product_id.detailed_type == 'service':
                    amount = lines.cost_price
                else:
                    amount = lines.qty_delivered * lines.cost_price
                mv_debit_lines = {
                            'product_id':lines.product_id.id,
                            'debit':amount,
                            'credit':0.0,
                            'date':line.close_date,
                            'journal_id':line.journal_id.id,
                            'company_id':line.company_id.id,
                            'account_id':lines.product_id.categ_id.property_stock_account_output_categ_id.id,
                            }
                mv_credit_lines = {    
                            'product_id':lines.product_id.id,
                            'debit':0.0,
                            'credit':amount,
                            'date':line.close_date,
                            'journal_id':line.journal_id.id,
                            'company_id':line.company_id.id,
                            'analytic_distribution': {
                                analytic_account_1.id: 100.0,
                            },
                            'account_id':line.journal_id.default_account_id.id,
                            }
                move_value['line_ids'].append((0, 0, mv_debit_lines))
                move_value['line_ids'].append((0, 0, mv_credit_lines))
            product_ids = line.products_line.mapped('product_id')
            project_analytic_line_ids = self.env['account.analytic.line'].search([('account_id', '=', line.analytic_account_id.id),('product_id','not in', product_ids.ids)])
            analytic_ids = []
            if project_analytic_line_ids:
                project_aml_ids = self.env['account.move.line'].browse(project_analytic_line_ids.mapped('move_line_id').ids)
                for am_line in project_aml_ids:
                    if am_line.balance > 0.0 and am_line.account_id.id == line.journal_id.default_account_id.id:
                        mv_debit_lines = {
                            #'product_id': am_line.product_id.id,
                            'debit': abs(am_line.balance),
                            'credit': 0.0,
                            'date': line.close_date,
                            'journal_id': am_line.journal_id.id,
                            'company_id': am_line.company_id.id,
                            'account_id': line.bbo_account_id.id,
                        }
                        mv_credit_lines = {
                            #'product_id': am_line.product_id.id,
                            'debit': 0.0,
                            'credit': abs(am_line.balance),
                            'date': line.close_date,
                            'journal_id': am_line.journal_id.id,
                            'company_id': am_line.company_id.id,
                            'analytic_distribution': {
                                analytic_account_1.id: 100.0,
                            },
                            'account_id': line.journal_id.default_account_id.id,
                        }
                        move_value['line_ids'].append((0, 0, mv_debit_lines))
                        move_value['line_ids'].append((0, 0, mv_credit_lines))
            
            project_analytic_line_idss = self.env['account.analytic.line'].search([('account_id', '=', line.analytic_account_id.id)])
            for acc_line in project_analytic_line_idss:
                analytic_ids.append(acc_line.id)
            line.account_analytic_line_ids = [(6,0, analytic_ids)]
            move_id = account_move_obj.create(move_value)
            move_id.action_post()
            line.close_move_id = move_id.id
            line.invoice_id = invoice_id.id
            
            line.state = 'done'
    
    
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
                'project_id': self.id,
                
            }
            lines = self.env['project.package.task.create.line'].create(pline_vals)
            line_ids.append(lines.id)
        wiz = self.env['project.package.task.create'].create({
            'product_lines': line_ids,
            'name':'/',
            'date':datetime.datetime.today()
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

    def _compute_cost_profit(self):
        for obj in self:
            if obj.state == 'done' and obj.close_move_id:
                obj.project_total_cost = sum(obj.close_move_id.line_ids.mapped('debit'))
                obj.project_total_profit = obj.contract_amount - sum(obj.close_move_id.line_ids.mapped('debit'))
            else:
                obj.project_total_cost = 0
                obj.project_total_profit = 0

    def _compute_invoice_count(self):
        for obj in self:
            analytic_id = str(obj.analytic_account_id.id)
            self.env.cr.execute("""
                                SELECT aml.id
                                FROM account_move_line aml
                                LEFT JOIN account_move am on aml.move_id = am.id
                                WHERE am.move_type = 'out_invoice' and analytic_distribution ? %s
                                """, [analytic_id])

            invoice_lines = self.env['account.move.line'].browse(
                [row[0] for row in self.env.cr.fetchall()]
            )
            obj.invoice_count = len(invoice_lines) if invoice_lines else 0

    def action_view_invoice(self):
        self.ensure_one()
        self.env.cr.execute("""
                SELECT am.id
                FROM account_move_line aml
                LEFT JOIN account_move am on am.id = aml.move_id
                WHERE am.move_type = 'out_invoice' and aml.analytic_distribution ? %s
            """, [str(self.analytic_account_id.id)]
        )


        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', [row[0] for row in self.env.cr.fetchall()])],
            "context": {"create": False, 'default_move_type': 'out_invoice'},
            "name": _("Invoices"),
            'view_mode': 'tree,form',
        }
        return result