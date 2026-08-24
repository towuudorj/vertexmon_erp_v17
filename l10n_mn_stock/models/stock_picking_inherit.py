# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    index_exists,
    is_html_empty,
)

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    
    amount_total = fields.Float(string='Amount total',
          compute='_compute_amount')
    amount_tax = fields.Float(string='Amount tax',
          compute='_compute_tax')
    amount_untaxed = fields.Float(string='Amount untaxed',
          compute='_compute_untaxed')
    receipt_date = fields.Date(string='Receipt Date')
    issue_date = fields.Date(string='Issue Date')
    delivery_user_id = fields.Many2one('res.users', string='Delivery User')
    project_type = fields.Selection([
        ('project', 'Project'),
        ('tender', 'Tender'),
    ], string='Type')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    ot_delivery_type = fields.Selection([('part_delivery','Partial delivery'),
                                        ('comp_delivery','Complete delivery'),
                                        ('final_delivery','Final delivery')],string='OT Delivery Type', default='comp_delivery')
    ot_address_type = fields.Selection([('site','Site'),
                                        ('office','Office')],string='OT Address Type')
    ot_contract = fields.Char(string='Purchasing Officer name/contact details', default='Your Reference: IT Goods Our Reference: CW2167225')
    ot_code = fields.Char(string='OT code', default=lambda self:self.env['ir.sequence'].next_by_code('stock.picking.ot'))
    purchase_count = fields.Integer(string='Purchase number', default=1)
    is_work_out = fields.Boolean(string='Is work out')
    approve_use_stamp = fields.Boolean('Approve use stamp')
    stamp_approved_user = fields.Many2one('res.users', string='Stamp Approved User')
    picking_type_code = fields.Selection(related='picking_type_id.code')
    signature_user_ids = fields.One2many('picking.signature.users', 'picking_id', string="Users signature")
    can_approve_signature = fields.Boolean(compute='_compute_signature_approval')


    def create_account_entry_move(self):
       for move in self.move_ids:
        for ml in move.move_line_ids:
            svl = self.env['stock.valuation.layer'].sudo().create({
                'stock_move_id': move.id,
                'product_id': move.product_id.id,
                'quantity': ml.quantity,
                'unit_cost': move.price_unit,
                'value': ml.quantity * move.price_unit,
                'company_id': move.company_id.id,
            })
    
            move._account_entry_move(
                qty=svl.quantity,
                description=move.name,
                svl_id=svl.id,   # ✅ FIX HERE
                cost=svl.value
            )

    @api.model
    def create(self, vals):
        if vals.get('approve_use_stamp', False):
            vals['stamp_approved_user'] = self.env.user.id
        res = super(stock_picking, self).create(vals)
        signature_user_obj = self.env['picking.signature.users'].sudo()
        employee_obj = self.env['hr.employee'].sudo()
        job_obj = self.env['hr.job'].sudo()

        for obj in res:
            env_user = self.env.user
            sale_id = self.env['sale.order'].browse(vals.get('sale_id', False))
            if sale_id:
                env_user = sale_id.user_id
            env_employee = env_user.employee_id
            signature_user_obj.create({
                'user_id': env_user.id,
                'type': 'picking_created', # Шаардах хуудас бичсэн
                'picking_id': obj.id,
                'sequence': 1,
            })
            if not sale_id:
                if env_employee.parent_id.id != env_employee.coach_id.id:
                    signature_user_obj.create({
                        'user_id': env_employee.coach_id.user_id.id if env_employee.coach_id else False,
                        'type': 'coach',  # Дадлагажуулагч
                        'picking_id': obj.id,
                        'sequence': 2,
                    })

                signature_user_obj.create({
                    'user_id': env_employee.parent_id.user_id.id if env_employee.parent_id else False,
                    'type': 'approved', # Зөвшөөрсөн
                    'picking_id': obj.id,
                    'sequence': 3,
                })

                job_id = job_obj.search([('name', '=', 'Санхүүгийн шинжээч')])
                financial_analyst = False
                if job_id:
                    financial_analyst = employee_obj.search([('job_id', '=', job_id.id), ('company_id', '=', obj.company_id.id)], limit=1, order='create_date asc')
                signature_user_obj.create({
                    'user_id': financial_analyst.user_id.id if financial_analyst else False,
                    'type': 'financial_analyst', # Санхүүгийн шинжээч
                    'picking_id': obj.id,
                    'sequence': 4,
                })

                job_id = job_obj.search([('name', 'ilike', 'нягтлан бодогч'),('name', '!=', 'Тооцооны нягтлан бодогч')])
                head = False
                if job_id:
                    accountants = employee_obj.search([('job_id', 'in', job_id.ids), ('company_id', '=', obj.company_id.id)], order='create_date asc')
                    for accountant in accountants:
                        if not head:
                            head = accountant.parent_id.user_id
                        if accountant.user_id:
                            signature_user_obj.create({
                                'user_id': accountant.user_id.id if accountant else False,
                                'type': 'accountant', # нягтлан бодогч
                                'picking_id': obj.id,
                                'sequence': 5,
                            })

                signature_user_obj.create({
                    'user_id': head.id if head else False,
                    'type': 'head', # Дарга
                    'picking_id': obj.id,
                    'sequence': 6,
                })

                job_id = job_obj.search([('name', '=', 'Нярав')])
                cashier = False
                if job_id:
                    cashier = employee_obj.search([('job_id', '=', job_id.id), ('company_id', '=', obj.company_id.id)], limit=1, order='create_date asc')
                signature_user_obj.create({
                    'user_id': cashier.user_id.id if cashier else False,
                    'type': 'issued_cashier', # Олгосон нярав
                    'picking_id': obj.id,
                    'sequence': 7,
                })

        return res

    def write(self, vals):
        if vals.get('approve_use_stamp', False):
            vals['stamp_approved_user'] = self.env.user.id
        return super(stock_picking, self).write(vals)
    
    def _compute_amount(self):
        
        for line in self:
            total = 0.0
            if line.amount_untaxed > 0.0:
                total = line.amount_tax + line.amount_untaxed
            line.amount_total = total

    def _compute_tax(self):
        for lin in self:
            total = 0.0
            if lin.state == 'done':
                for line in lin.move_line_ids_without_package:
                    total +=line.tax_amount
            else:
               for line in lin.move_ids_without_package:
                   total +=line.tax_amount
            lin.amount_tax = total

    def _compute_untaxed(self):
        for lin in self:
            total = 0.0
            if lin.move_ids:
                for line in lin.move_ids:
                    if line.untaxed_amount > 0.0:
                        total +=line.untaxed_amount
                    else:
                        total +=line.price_subtotal
                    
            else:
                for line in lin.move_ids_without_package:
                    if line.untaxed_amount > 0.0:
                        total +=line.untaxed_amount
                    else:
                        total +=line.price_subtotal
            lin.amount_untaxed = total

    def button_validate(self):
        draft_picking = self.filtered(lambda p: p.state == 'draft')
        draft_picking.action_confirm()
        for move in draft_picking.move_ids:
            if float_is_zero(move.quantity, precision_rounding=move.product_uom.rounding) and\
               not float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                move.quantity = move.product_uom_qty
        stock_landed_cost_obj = self.env['stock.landed.cost']
        if self.sale_id:
            if self.sale_id.opportunity_id.purchase_order_ids:
                for pur in self.sale_id.opportunity_id.purchase_order_ids:
                    if pur.is_expense == True:
                        stock_landed_id = stock_landed_cost_obj.search([('po_ids','in',[pur.id])])
                        if len (stock_landed_id) == 0:
                            raise UserError(_("Зардал бүртгэгдээгүй байгаа тул батлах боломжгүйг анхаарна уу!"))
                        else:
                            for cost in stock_landed_id:
                                if cost.state == 'draft':
                                    raise UserError(_("Зардал батлагдаагүй байгаа тул батлах боломжгүйг анхаарна уу!"))
                                    
            
        # Sanity checks.
        if not self.env.context.get('skip_sanity_check', False):
            self._sanity_check()
        self.message_subscribe([self.env.user.partner_id.id])

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
                lambda p: p.picking_type_id.create_backorder != 'always'
            )
        pickings_to_backorder = self - pickings_not_to_backorder
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
        report_actions = self._get_autoprint_report_actions()
        another_action = False
        if self.user_has_groups('stock.group_reception_report'):
            pickings_show_report = self.filtered(lambda p: p.picking_type_id.auto_show_reception_report)
            lines = pickings_show_report.move_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity and not m.move_dest_ids)
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env['stock.location']._search([('id', 'child_of', pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids), ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                        ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                        ('product_qty', '>', 0),
                        ('location_id', 'in', wh_location_ids),
                        ('move_orig_ids', '=', False),
                        ('picking_id', 'not in', pickings_show_report.ids),
                        ('product_id', 'in', lines.product_id.ids)], limit=1):
                    action = pickings_show_report.action_view_reception_report()
                    action['context'] = {'default_picking_ids': pickings_show_report.ids}
                    if not report_actions:
                        return action
                    another_action = action
        if report_actions:
            return {
                'type': 'ir.actions.client',
                'tag': 'do_multi_print',
                'params': {
                    'reports': report_actions,
                    'anotherAction': another_action,
                }
            }
        purchase_manager = False
        purchase_order = False
        crm_id = False
        for mv in self.move_ids_without_package:
            purchase_manager = mv.purchase_line_id.order_id.requisition_id.crm_lead_id.user_id
            crm_id = mv.purchase_line_id.order_id.requisition_id.crm_lead_id.code
            purchase_order = mv.purchase_line_id.order_id
        if purchase_manager:
            mails = []
            for manager in purchase_manager:
                if manager.employee_id and manager.employee_id.work_email:
                    mails.append(manager.employee_id.work_email)
                    continue
                if manager.partner_id and manager.partner_id.email:
                    mails.append(manager.partner_id.email)
            # Send email notification
            if mails:
                purchase_url = f'/web#id={purchase_order.id}&model=purchase.order&view_type=form'
                self.env['mail.mail'].create({
                    'email_to': ','.join(mails),
                    'subject': f'Таны Сэжим : {crm_id} - ын худалдан авалтын барааг хүлээн авсан байна.',
                    'body_html': f'Худалдан авалтын дэлгэрэнгүй мэдээлэл харах холбоос. <a href="{purchase_url}">{purchase_order.name}</a>',
                }).send()
        #if self.sale_id.invoice_ids:
        #    self.sale_id._create_invoices()
        return True

    def _compute_signature_approval(self):
        env_user = self.env.user
        for obj in self:
            user_line = obj.signature_user_ids.filtered(lambda s: (s.user_id.id == env_user.id and not s.substitute_user)
                                                                  or s.substitute_user.id == env_user.id)
            if obj.signature_user_ids and user_line:
                same_type_unapprove_line = obj.signature_user_ids.filtered(lambda s: s.type in user_line.mapped('type') and not s.is_approve_signature)
                obj.can_approve_signature = True if same_type_unapprove_line else False
            else:
                obj.can_approve_signature = False

    def link_signature(self):
        env_user = self.env.user
        user_obj = self.env['res.users']
        for obj in self:
            signature_user_line = obj.signature_user_ids.filtered(lambda s: ((s.user_id.id == env_user.id and not s.substitute_user)
                                                                             or s.substitute_user.id == env_user.id)
                                                                             and not s.is_approve_signature)
            if signature_user_line:
                for line in signature_user_line:
                    if line.type in ['picking_created', 'coach']:
                        approval_user_id = obj.signature_user_ids.filtered(lambda s: s.type == 'approved').user_id
                        if line.user_id.sudo().employee_id.job_id and 'захирал' in line.user_id.sudo().employee_id.job_id.name or not approval_user_id:
                            notif_line = obj.signature_user_ids.filtered(lambda s: s.type not in ['approved', 'coach', 'picking_created'] and not s.is_approve_signature)
                            if notif_line:
                                users = user_obj
                                for n_line in notif_line:
                                    users |= n_line.user_id if not n_line.substitute_user else n_line.substitute_user
                                self.send_notif_mail(users)
                            continue
                        if line.type == 'picking_created':
                            domain = ['approved', 'coach']
                        else:
                            domain = ['approved']
                        notif_line = obj.signature_user_ids.filtered(lambda s: s.type in domain and not s.is_approve_signature)
                        if notif_line:
                            users = user_obj
                            for n_line in notif_line:
                                users |= n_line.user_id if not n_line.substitute_user else n_line.substitute_user
                            self.send_notif_mail(users)
                    if line.type == 'approved':
                        notif_line = obj.signature_user_ids.filtered(lambda s: s.type not in ['approved', 'coach', 'picking_created'] and
                                                                                        not s.is_approve_signature)
                        if notif_line:
                            users = user_obj
                            for n_line in notif_line:
                                users |= n_line.user_id if not n_line.substitute_user else n_line.substitute_user
                            self.send_notif_mail(users)

                signature_user_line.is_approve_signature = True

    def send_notif_mail(self, user_ids):
        emails = []
        for user in user_ids:
            if user.employee_id.work_email:
                emails.append(user.employee_id.work_email)
                continue

            if user.partner_id.email:
                emails.append(user.partner_id.email)
                continue

            if user.login:
                emails.append(user.login)
                continue
        if emails:
            picking_url = f'/web#id={self.id}&model=stock.picking&view_type=form'
            created = self.signature_user_ids.filtered(lambda s: s.type == 'picking_created').user_id
            self.env['mail.mail'].create({
                'email_to': ','.join(emails),
                'subject': f'Шаардах хуудас {self.name} -ын гарын үсэг зуруулах хүсэлт илгээсэн байна.',
                'body_html': f"""<br>
                            Шаардах хуудас: {self.name} <br>
                            Борлуулалтын ажилтан: {created.name} <br>
                            Доорх товчоор дамжин орж зурна уу
                            <br><br>
                             <a href="{picking_url}" style="box-sizing:border-box;background-color: #875A7B; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">
                                 Шаардах хуудас
                             </a><br><br>
                             """

            }).send()

    def get_signature_users(self):
        self.ensure_one()
        user_dict = {}
        for line in self.signature_user_ids:
            if line.is_approve_signature:
                user_dict[line.type] = line.user_id if not line.substitute_user else line.substitute_user
        return user_dict


class PickingSignatureUsers(models.Model):
    _name = 'picking.signature.users'
    _order = 'sequence asc'

    user_id = fields.Many2one('res.users', 'User')
    substitute_user = fields.Many2one('res.users', 'Substitute User')
    parent_create_user = fields.Many2one(related='picking_id.create_uid')
    type = fields.Selection([
            ('approved', 'Approved'),
            ('coach', 'Coach'),
            ('issued_cashier', 'Issued Cashier'),
            ('accountant', 'Accountant'),
            ('picking_created', 'Picking Created'),
            ('financial_analyst', 'Financial Analyst'),
            ('head', 'Head'),
    ])
    is_approve_signature = fields.Boolean(default=False)
    picking_id = fields.Many2one('stock.picking', 'Picking', ondelete='cascade')
    sequence = fields.Integer('Sequence')