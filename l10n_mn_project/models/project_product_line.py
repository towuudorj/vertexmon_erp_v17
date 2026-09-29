# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from odoo.tools import SQL



class ProjectProductsLine(models.Model):
    _name = "project.products.line"
    _description = "Project Product Line"
    _order = 'project_id, sequence, id'


    @api.depends('product_id', 'product_id.default_code', 'product_id.name', 'project_id.products_line.product_id')
    def _compute_is_duplicate_product(self):
        # Барааны код (default_code)/нэрээр харьцуулна — ижил бодит бараа өөр
        # (давхардсан) product.product бичлэгээр орсон тохиолдлыг ч оруулна.
        for line in self:
            if not line.product_id or not line.project_id:
                line.is_duplicate_product = False
                continue
            key = line.product_id.default_code or line.product_id.name
            siblings = line.project_id.products_line.filtered(
                lambda l: l.product_id and (l.product_id.default_code or l.product_id.name) == key
            )
            line.is_duplicate_product = len(siblings) > 1

    @api.depends('project_id')
    def _compute_qty_available(self):
        quant_obj = self.env['stock.quant']
        purchase_obj = self.env['purchase.order']
        for line in self:
            qty = 0
            quant = quant_obj.search([('location_id','=',line.project_id.warehouse_id.lot_stock_id.id),('product_id','=',line.product_id.id)])
            if quant:
                quant = quant.filtered(lambda q: q.inventory_quantity_auto_apply > 0.0)
            if quant:
                for qt in quant:
                    qty +=qt.inventory_quantity_auto_apply
            else:
                qty = 0
            line.qty_available = qty
    
    @api.depends('project_id')
    def _compute_qty_delivered(self):
        for line in self:
            qty = 0
            for pick in line.project_id.picking_ids:
                for pur in pick.move_ids_without_package:
                    if pur.product_id.id == line.product_id.id and pick.state == 'done':
                        qty +=pur.quantity
                return_pickings = pick.move_ids.returned_move_ids.mapped('picking_id')
                if return_pickings:
                    for ret in return_pickings:
                        for pur in ret.move_ids_without_package:
                            if pur.product_id.id == line.product_id.id and ret.state == 'done':
                                qty -= pur.quantity
            line.qty_delivered = qty
    
    project_id = fields.Many2one('project.project', string='Project', index=True, required=True, ondelete='cascade')
    is_duplicate_product = fields.Boolean(string='Давхардал', compute='_compute_is_duplicate_product')
    
    sequence = fields.Integer(string='Sequence', default=1)
    product_id = fields.Many2one('product.product', string='Product', 
                    domain=[('purchase_ok', '=', True)], change_default=True)

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, required=True, precompute=True)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float(string='Price', required=True, digits='Product Price')
    cost_price = fields.Float(string='Cost Price', required=True, digits='Product Price')
    qty_available = fields.Float(string='Available QTY', compute='_compute_qty_available', required=True, digits='Product', readonly=True, default=0)
    qty_delivered = fields.Float(string='Delivered',  required=True, digits='Product', readonly=True, 
                                        default=0, compute="_compute_qty_delivered")
    price_total = fields.Float(string='Total Price', readonly=True)
    cost_total = fields.Float(string='Total Cost', readonly=True)
    delivery_cost = fields.Float(string='Delivery cost', compute="compute_delivery_cost")
    qty_available_cost = fields.Float(string='Qty available cost', compute="compute_qty_available_cost")
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    purchase_type = fields.Selection([('local','Local'),
                                    ('foreign','Foreign')],string='Purchase Type',)
    is_task = fields.Boolean(string='Task', default=False)
    is_purchase = fields.Boolean(string='Purchase', default=False)
    purchase_manager_id = fields.Many2one('res.users', string='Purchase Manager')
    last_qty = fields.Float(string='Last qty', compute="_action_compute_qty")
    pur_qty = fields.Float(string='Purchase qty')
    picking_ids = fields.Many2many('stock.picking', string='Picking')
    change_cost = fields.Float(string='Change cost', compute="action_change_cost")
    
    
    
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group('account.group_account_manager'):
            for vals in vals_list:
                project_id = vals.get('project_id')
                product_id = vals.get('product_id')
                if project_id and product_id:
                    project = self.env['project.project'].browse(project_id)
                    if project.state == 'process':
                        raise UserError(
                            "Эрх бүхий ажилтан биш тул засварлах боломжгүйг анхаарна уу!"
                        )
        res =  super().create(vals_list)
        for obj in res:
            obj.cost_price = obj.product_id.standard_price
            obj.onchange_product_qty()
        return res
    
    def write(self, vals):
        for order in self:
            if order.project_id.state == 'process':
                if 'product_id' in vals or 'product_qty' in vals or 'purchase_type' in vals or 'purchase_manager_id' in vals or 'cost_price' in vals or 'price_unit' in vals:
                    if not self.env.user.has_group('account.group_account_manager'):
                        raise UserError((u"Эрх бүхий ажилтан биш тул засварлах боломжгүйг анхаарна уу !"))
            if 'product_id' in vals and vals.get('product_id') != order.product_id.id and order.qty_delivered > 0:
                raise UserError(_("Уг бараагаар төслөөс зарлага хийгдсэн тул барааг өөрчлөх боломжгүй!"))
            if 'product_qty' in vals and vals.get('product_qty') < order.qty_delivered:
                raise UserError(_("Тоо хэмжээг зарлага хийгдсэн тооноос бага байлгах боломжгүй! Зарлага хийгдсэн тоо: %s") % order.qty_delivered)
        return super(ProjectProductsLine, self).write(vals)
    
    
    def action_change_cost(self):
        for line in self:
            cost = 0
            for lines in line.project_id.purchase_ids:
                for list in lines.order_line:
                    cost = ((list.price_unit * lines.currency_rate) + line.change_cost)/2
            line.change_cost = cost
            
    
    
    def compute_delivery_cost(self):
        for line in self:
            delivery_cost = 0
            if line.product_id and line.product_id.detailed_type == 'service' and line.project_id.analytic_account_id:
                query = self.env['account.move.line']._search(
                    [('move_id.move_type', 'in', self.env['account.move'].get_purchase_types())])
                query.add_where(
                    SQL(
                        "%s && %s",
                        [str(line.project_id.analytic_account_id.id)],
                        self.env['account.move.line']._query_analytic_accounts(),
                    )
                )
                query_string, query_param = query.select('DISTINCT account_move_line.move_id')
                self._cr.execute(query_string, query_param)
                move_ids = [l.get('move_id') for l in self._cr.dictfetchall()]
                invoice_ids = self.env['account.move'].browse(move_ids)
                invoice_line_ids = False
                if invoice_ids:
                    invoice_line_ids = invoice_ids.mapped('invoice_line_ids').filtered(lambda i_line: (line.product_id.id == i_line.purchase_line_id.product_id.id
                                                                                                       or i_line.product_id.id == line.product_id.id)
                                                                                                      and i_line.move_id.state == 'posted')
                if invoice_line_ids:
                    delivery_cost = abs(sum(invoice_line_ids.mapped('price_total')))
                else:
                    delivery_cost = 0
            else:
                if line.cost_price > 0.0 and line.qty_delivered > 0.0:
                    delivery_cost = line.cost_price * line.qty_delivered
            line.delivery_cost = delivery_cost
        self.mapped('project_id')._amount_all()
        
    def compute_qty_available_cost(self):
        for line in self:
            available_cost = 0
            if line.cost_price > 0.0 and line.qty_available > 0.0:
                available_cost = line.cost_price * line.qty_available
                
            line.qty_available_cost = available_cost
    
    def _action_compute_qty(self):
        for line in self:
            line.last_qty = line.product_qty - line.qty_delivered
            
    @api.onchange('cost_price')
    def onchange_cost_price(self):
        for line in self:
            if line.product_qty > 0:
                line.cost_total = line.cost_price * line.product_qty
    
    @api.onchange('price_unit')
    def onchange_price_unit(self):
        if self.product_qty > 0:
            self.price_total = self.price_unit * self.product_qty
            
    @api.onchange('product_qty')
    def onchange_product_qty(self):
        
        if not self.product_id:
            return
        
        self.price_total = self.price_unit * self.product_qty
        self.cost_total = self.cost_price * self.product_qty
   
        
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            return
        # pricelist = self.company_id.base_pricelist_id
        # sale_pricelist = self.company_id.sale_pricelist_id
        
        # # Reset date, price and quantity since _onchange_quantity will provide default values
        # list_price = pricelist._get_product_price(self.product_id , 1, self.project_id.partner_id)
        
        self.price_unit = self.product_id.list_price
        self.change_cost = self.product_id.standard_price
        self.cost_price = self.product_id.standard_price
        self.name = self.product_id.name
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        # 'net_on_hand': obj.with_context({'warehouse': warehouse, 'to_date': end_date}).qty_available
        print( 'qty avail============', self.with_context({'to_date': datetime.today()}).qty_available)
        self.qty_available = self.with_context({'to_date': datetime.today()}).qty_available
       
        self.price_total = self.price_unit * self.product_qty
        self.cost_total = self.cost_price * self.product_qty

    def _get_invoiced_amount(self):
        self.ensure_one()
        if not self.project_id.analytic_account_id:
            return 0.0
        aml = self.env['account.move.line'].search([
            ('product_id', '=', self.product_id.id),
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.state', '=', 'posted'),
            ('purchase_line_id.order_id.analytic_id', '=', self.project_id.analytic_account_id.id),
        ])
        return sum(aml.mapped('price_subtotal'))

    def _check_budget_threshold(self):
        job_obj = self.env['hr.job']
        employee_obj = self.env['hr.employee']
        for line in self:
            if not line.product_id.project_budget_monitor or not line.price_total:
                continue
            issued_amount = line._get_invoiced_amount()
            if issued_amount < line.price_total * 0.9:
                continue
            manager = line.project_id.user_id.employee_id.parent_id

            job_id = job_obj.search([('name', '=', 'Санхүүгийн шинжээч')])
            financial_analyst = False
            if job_id:
                financial_analyst = employee_obj.search([
                    ('job_id', '=', job_id.id),
                    ('company_id', '=', line.project_id.company_id.id),
                ], limit=1, order='create_date asc')

            job_id = job_obj.search([('name', '=', 'Ахлах нягтлан бодогч')])
            head_accountant = False
            if job_id:
                head_accountant = employee_obj.search([
                    ('job_id', '=', job_id.id),
                    ('company_id', '=', line.project_id.company_id.id),
                ], limit=1, order='create_date asc')

            emails = []
            if manager and manager.work_email:
                emails.append(manager.work_email)
            if financial_analyst and financial_analyst.work_email:
                emails.append(financial_analyst.work_email)
            if head_accountant and head_accountant.work_email:
                emails.append(head_accountant.work_email)
            if not emails:
                continue

            project_url = f'/web#id={line.project_id.id}&model=project.project&view_type=form'
            self.env['mail.mail'].create({
                'email_to': ','.join(emails),
                'subject': f'Төслийн төсвийн анхааруулга: {line.project_id.name} - {line.product_id.name}',
                'body_html': (
                    f'Төсөл: {line.project_id.name}<br/>'
                    f'Бараа: {line.product_id.name}<br/>'
                    f'Нийт зарлагдсан дүн: {issued_amount:,.2f} / Төлөвлөсөн дүн: {line.price_total:,.2f}<br/>'
                    f'Зарлагадсан дүн нь төлөвлөсөн дүнгийн 90%-иас давлаа.<br/>'
                    f'<a href="{project_url}">{line.project_id.name}</a>'
                ),
            }).send()

