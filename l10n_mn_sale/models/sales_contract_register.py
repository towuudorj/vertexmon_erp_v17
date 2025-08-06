# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleContractRegister(models.Model):
    _name = 'sales.contract.register'
    _description = 'Sales Contract Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one(
        string='Partner', 
        comodel_name='res.partner', 
        required=True)
    confirm_date = fields.Date(string='Confirm date', 
                               readonly=True)
    contract_number_auto = fields.Char(string='Contract number auto', readonly=True)
    name = fields.Char(string='Contract name', 
                       required=True)
    contract_number = fields.Char(string='Contract number')
    start_date = fields.Date(string='Start date', 
                             required=True)
    end_date = fields.Date(string='End date', 
                           required=True)
    contract_amount = fields.Float(string='Contract amount', 
                                   required=True)
    currency_id = fields.Many2one(
        string='Currency', 
        comodel_name='res.currency', 
        required=True)
    contract_type = fields.Many2one(
        comodel_name='sales.contract.type',
        string='Contract type')
    state = fields.Selection([('draft', 'Draft'), 
                              ('send_draft', 'Send draft'),
                              ('confirmed', 'Confirmed'), 
                              ('payment_waiting', 'Payment waiting'),
                              ('closed', 'Closed'),
                              ('deposit', 'Deposit'),
                              ('cancel', 'Cancel')],
                             string='State', 
                             default='draft', 
                             tracking=True)
    sales_manager_id = fields.Many2one('res.users', 
                                       string='Sales Manager')
    sales_team_id = fields.Many2one('crm.team', 
                                    string='Sales Team')
    sales_ids = fields.One2many('sale.order', 'contract_id', 
                                string='Sales')
    sales_count = fields.Integer(string='Sales count', compute='_compute_sales_count')
    invoice_ids = fields.Many2one('account.move', string='Invoice')
    invoice_count = fields.Integer(string='Invoice count', compute='_compute_invoice_count')
    project_count = fields.Integer(string='Project count', compute="_compute_project_count")
    payment_term_id = fields.Many2one('account.payment.term',string='Payment term')
    reg_date = fields.Date(string='Register date', 
                           default=fields.Date.today)
    reg_user_id = fields.Many2one('res.users', 
                                  string='Register user', 
                                  default=lambda self: self.env.user)
    note = fields.Text(string='Note')
    local_type = fields.Selection([('non_project', 'Non Project'),
                                    ('project','Project')], string='Local type', default='non_project')
    project_id = fields.Many2one('project.project', 
                                 string='Project', 
                                 readonly=True)
    line_ids = fields.One2many('sales.contract.register.line', 'contract_id', 
                               string='Lines')


    def _compute_project_count(self):
        for line in self:
            project_ids = self.env['project.project'].search([('sale_contract_id', '=', line.id)])
            line.project_count = len(project_ids)

    def _compute_invoice_count(self):
        for line in self:
            move_ids = self.env['account.move'].search([('contract_id', '=', line.id),('state', '!=', 'cancel')])
            line.invoice_count = len(move_ids)


    def _compute_sales_count(self):
        for line in self:
            sale_orders = self.env['sale.order'].search([('contract_id', '=', line.id),('state', '!=', 'cancel')])
            line.sales_count = len(sale_orders)


    def action_project_order(self):
        self.ensure_one()
        return {
            'name': _('Projects'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'tree,form',
            'domain': [('sale_contract_id', '=', self.id)],
        }


    def action_invoice_order(self):
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('contract_id', '=', self.id)],
        }

    def action_sale_order(self):
        self.ensure_one()
        return {
            'name': _('Sales'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('contract_id', '=', self.id)],
        }

    def action_create_project(self):
        if self.project_id:
            raise UserError('Project already exists')
        else:
            project = self.env['project.project'].create({
                                                        'name': self.name,
                                                        'partner_id': self.partner_id.id,
                                                        'company_id': self.company_id.id,
                                                        'user_id': self.sales_manager_id.id,
                                                        'sale_contract_id': self.id
                                                        })
            self.project_id = project.id

    def action_confirm(self):
        self.state = 'confirmed'
        self.contract_number_auto = self.env['ir.sequence'].next_by_code('sales.contract.register')
        self.confirm_date = fields.Date.today()

    def action_closed(self):
        self.state = 'closed'
    
    def action_send_draft(self):
        self.state = 'send_draft'
    
    def action_payment_waiting(self):
        self.state = 'payment_waiting'
    
    def action_deposit(self):
        self.state = 'deposit'

    def action_cancel(self):
        self.state = 'cancel'


class SaleContractType(models.Model):
    _name = 'sales.contract.type'
    _description = 'Sales Contract Type'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id)


class SaleContractRegisterLine(models.Model):
    _name = 'sales.contract.register.line'
    _description = 'Sales Contract Register line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    contract_id = fields.Many2one('sales.contract.register', string='Contract')
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Reference')
    uom_id = fields.Many2one('uom.uom', string='Uom')
    price_unit = fields.Float(string='Price unit')
    qty = fields.Float(string='Quantity')
    price_subtotal = fields.Float(string='Price subtotal')
