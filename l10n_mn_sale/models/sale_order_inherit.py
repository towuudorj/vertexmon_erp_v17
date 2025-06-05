# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, AccessError
from odoo.fields import Command
from itertools import groupby
from odoo.tools import float_is_zero, format_amount, format_date, html_keep_url, is_html_empty


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _compute_default_partner_bank_id(self):
        """ Default partner bank account for sale order """
        bank_id = self.env['res.partner.bank'].search([('acc_number', '=', '5002411886')])
        if bank_id:
            return bank_id[0].id
        else:
            return False

    expire_day = fields.Integer(string="Expire day", 
                                default=14)
    supply_date = fields.Char(string='Supply date',
                              default=u'14-28 хоног')
    cancel_reason = fields.Char(string='Cancel reason')
    supply_days = fields.Integer(string='Supply days')
    note = fields.Html(
        string="Terms and conditions",
        compute='_compute_note',
        store=True, readonly=False, precompute=True,
        default=u'Үнийн саналд НӨАТ багтсан.')
    sales_type = fields.Selection([('direct', 'Direct'),
                                   ('tender', 'Tender'),
                                   ('project', 'Project')],
                                  string='Sales type',
                                  default='direct',
                                  required=True)
    partner_type = fields.Many2one('partner.type.register', 
                                   string='Partner type',
                                   required=True,
                                   compute='_compute_partner_type',
                                   store=True, readonly=False, precompute=True, check_company=True,  # Unrequired company
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    contract_id = fields.Many2one('sales.contract.register', 
                                  string='Contract')
    contract_count = fields.Integer(string='Contract', 
                                    compute="_compute_contract")
    partner_bank_id = fields.Many2one('res.partner.bank', 
                                   string='Bank Account Number',
                                   domain="[('partner_id.ref_company_ids', 'parent_of', company_id)]",
                                   required=False,
                                   default=_compute_default_partner_bank_id)
    purchase_request_ids = fields.Many2many('purchase.requisition', string='Purchase requisition')
    purchase_request_count = fields.Integer(string='Purchase requisition', 
                                            compute="_compute_purchase_request")
    sale_order_type = fields.Selection([('direct', 'Direct'),
                                        ('non_direct', 'Non direct'),
                                        ('quotation', 'Quotation')], string='Sale order type', default='direct',
                                        required=True)

                                        
    #Тоололт
    def _compute_purchase_request(self):
        for sale in self:
            purchase_requests = self.env['purchase.requisition'].search([('sale_id', '=', sale.id),('state', '!=', 'cancel')])
            sale.purchase_request_ids = purchase_requests
            sale.purchase_request_count = len(purchase_requests)
    
    def action_view_purchase_requisition(self, purchases=False):
        if not purchases:
            purchases = self.mapped('purchase_request_ids')
        action = self.env['ir.actions.actions']._for_xml_id('purchase_requisition.action_purchase_requisition')
        if len(purchases) > 1:
            action['domain'] = [('id', 'in', purchases.ids)]
        elif len(purchases) == 1:
            form_view = [(self.env.ref('purchase_requisition.view_purchase_requisition_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = purchases.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
        }
        if len(self) == 1:
            context.update({
                'default_sale_id': self.id,
            })
        action['context'] = context
        return action


    def purchase_request_create(self):
        for sale in self:
            context = dict(self._context)
            context.pop("default_type", None)
            line_ids = self.env['purchase.requisition.line']
            for lines in sale.order_line:
                if lines.purchase_user_id:
                    type_id = self.env['purchase.requisition.type'].search([], limit=1)
                    purchase_requests = self.env['purchase.requisition'].search([('sale_id', '=', sale.id),
                                                                                ('purchase_user_id', '=', lines.purchase_user_id.id),
                                                                                ('send_date','=',self.send_date),
                                                                                ('state', '=', 'draft')])
                    if not purchase_requests:
                        datas = {
                            'sale_id': sale.id,
                            'user_id': sale.user_id.id,
                            'company_id': sale.company_id.id,
                            'origin': sale.name,
                            'state': 'draft',
                            'type_id': type_id.id,
                            'purchase_user_id':lines.purchase_user_id.id,
                            'send_date': self.send_date,
                        }
                        purchase_request_id = self.env['purchase.requisition'].with_context(context).create(datas)

                        sale.purchase_request_ids = [(4,purchase_request_id.id)]
                        if lines.purchase_user_id.id == purchase_request_id.purchase_user_id.id:
                            line_ids = self.env['purchase.requisition.line'].search([('requisition_id', '=', purchase_requests.id), 
                                                                                  ('sale_line_id', '=', lines.id)])
                            if not line_ids:
                                line_data = {
                                            'product_id': lines.product_id.id,
                                            'product_description_variants': lines.name,
                                            'product_qty': lines.qty,
                                            'product_uom_id': lines.uom_id.id,
                                            'priority': lines.priority,
                                            'requisition_id': purchase_request_id.id,
                                            'currency_id': purchase_requests.currency_id.id,
                                            'price_unit':0,
                                            'sale_line_id':lines.id,
                                            }
                                line_ids.create(line_data)
                            lines.request_line_id = line_ids.id
                    else:
                        sale.purchase_request_ids = [(4,purchase_requests.id)]
                        if lines.purchase_user_id.id == purchase_requests.purchase_user_id.id:
                            line_ids = self.env['purchase.requisition.line'].search([('requisition_id', '=', purchase_requests.id), 
                                                                                  ('sale_line_id', '=', lines.id)])
                            if not line_ids:
                                line_data = {
                                            'product_id': lines.product_id.id,
                                            'product_description_variants': lines.name,
                                            'product_qty': lines.qty,
                                            'priority': lines.priority,
                                            'product_uom_id': lines.uom_id.id,
                                            'requisition_id': purchase_requests.id,
                                            'lead_line_id':lines.id,
                                            'currency_id': purchase_requests.currency_id.id,
                                            'price_unit':0,
                                            }
                                
                                line_ids.create(line_data)
                            lines.request_line_id = line_ids.id
                #else:
                #    raise UserError(_('Бараа бүртгээгүй байгаа тул бүртгэнэ үү!'))
            #else:
            #    raise UserError(_('Үнэ судлуулах хүсэлт үүссэн байгаа тул анхаарна уу!'))
        return True
    



    def action_confirm(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm cancelled SO's
        """
        if not all(order._can_be_confirmed() for order in self):
            raise UserError(_(
                "The following orders are not in a state requiring confirmation: %s",
                ", ".join(self.mapped('display_name')),
            ))

        self.order_line._validate_analytic_distribution()

        for order in self:
            #if order.opportunity_id:
            #    for po_rq in order.opportunity_id.purchase_request_ids:
            #        if po_rq.status == 'quotation_st':
            #            po_rq.quotation_done()
            order.validate_taxes_on_sales_order()
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])

        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_lock()
        
        if not self.env.user.has_group('sales_team.group_sale_manager') and self.invoice_policy == 'delivery':
            raise UserError(_(
                u"Батлах эрх бүхий ажилтнаар батлуулна уу!",
            ))


        return True
    
    def _action_cancel(self):
        inv = self.invoice_ids.filtered(lambda inv: inv.state in ('draft','posted'))
        inv.button_cancel()
        return self.write({'state': 'cancel'})

    def _create_invoices(self, grouped=False, final=False, date=None):
        """ Create invoice(s) for the given Sales Order(s).

        :param bool grouped: if True, invoices are grouped by SO id.
            If False, invoices are grouped by keys returned by :meth:`_get_invoice_grouping_keys`
        :param bool final: if True, refunds will be generated if necessary
        :param date: unused parameter
        :returns: created invoices
        :rtype: `account.move` recordset
        :raises: UserError if one of the orders has no invoiceable lines.
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id).with_context(lang=order.partner_invoice_id.lang)

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        Command.create(
                            order._prepare_down_payment_section_line(sequence=invoice_item_sequence)
                        ),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                invoice_line_vals.append(
                    Command.create(
                        line._prepare_invoice_line(sequence=invoice_item_sequence)
                    ),
                )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals['invoice_date'] = self.effective_date
            invoice_vals_list.append(invoice_vals)
        #if not invoice_vals_list and self._context.get('raise_if_nothing_to_invoice', True):
        #    raise UserError(self._nothing_to_invoice_error_message())

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(
                invoice_vals_list,
                key=lambda x: [
                    x.get(grouping_key) for grouping_key in invoice_grouping_keys
                ]
            )
            for _grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                    sequence += 1

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_move_type()
        for move in moves:
            if final:
                # Downpayment might have been determined by a fixed amount set by the user.
                # This amount is tax included. This can lead to rounding issues.
                # E.g. a user wants a 100€ DP on a product with 21% tax.
                # 100 / 1.21 = 82.64, 82.64 * 1,21 = 99.99
                # This is already corrected by adding/removing the missing cents on the DP invoice,
                # but must also be accounted for on the final invoice.

                delta_amount = 0
                for order_line in self.order_line:
                    if not order_line.is_downpayment:
                        continue
                    inv_amt = order_amt = 0
                    for invoice_line in order_line.invoice_lines:
                        if invoice_line.move_id == move:
                            inv_amt += invoice_line.price_total
                        elif invoice_line.move_id.state != 'cancel':  # filter out canceled dp lines
                            order_amt += invoice_line.price_total
                    if inv_amt and order_amt:
                        # if not inv_amt, this order line is not related to current move
                        # if no order_amt, dp order line was not invoiced
                        delta_amount += (inv_amt * (1 if move.is_inbound() else -1)) + order_amt

                if not move.currency_id.is_zero(delta_amount):
                    receivable_line = move.line_ids.filtered(
                        lambda aml: aml.account_id.account_type == 'asset_receivable')[:1]
                    product_lines = move.line_ids.filtered(
                        lambda aml: aml.display_type == 'product' and aml.is_downpayment)
                    tax_lines = move.line_ids.filtered(
                        lambda aml: aml.tax_line_id.amount_type not in (False, 'fixed'))
                    if tax_lines and product_lines and receivable_line:
                        line_commands = [Command.update(receivable_line.id, {
                            'amount_currency': receivable_line.amount_currency + delta_amount,
                        })]
                        delta_sign = 1 if delta_amount > 0 else -1
                        for lines, attr, sign in (
                            (product_lines, 'price_total', -1 if move.is_inbound() else 1),
                            (tax_lines, 'amount_currency', 1),
                        ):
                            remaining = delta_amount
                            lines_len = len(lines)
                            for line in lines:
                                if move.currency_id.compare_amounts(remaining, 0) != delta_sign:
                                    break
                                amt = delta_sign * max(
                                    move.currency_id.rounding,
                                    abs(move.currency_id.round(remaining / lines_len)),
                                )
                                remaining -= amt
                                line_commands.append(Command.update(line.id, {attr: line[attr] + amt * sign}))
                        move.line_ids = line_commands

            move.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': move, 'origin': move.line_ids.sale_line_ids.order_id},
                subtype_xmlid='mail.mt_note',
            )
        return moves


    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for line in self.order_line:
            if line.display_type == 'line_section':
                # Only invoice the section if one of its lines is invoiceable
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                pending_section = line
                invoiceable_line_ids.append(line.id)
                continue

            if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note' or line.display_type==False:
                if line.is_downpayment:
                    # Keep down payment lines separately, to put them together
                    # at the end of the invoice, in a specific dedicated section.
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = None
                invoiceable_line_ids.append(line.id)
        return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)


    @api.model_create_multi
    def create(self, vals_list):
        user_obj = self.env['res.users']
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if vals.get('name', _("New")) == _("New"):
                sequence_date = fields.Datetime.to_datetime(vals['date_order'])
                seq_year = str(sequence_date.year)[2:]
                seq_month = sequence_date.month
                seq_day = sequence_date.day
                seq_number = user_obj.browse(vals['user_id']).sq_number
                seq_qty = 1
                last_name = self.env['sale.order'].search([('state','!=','cancel'),('user_id','=',vals['user_id'])], order='id desc', limit=1)
                if last_name:
                    last_name = last_name.name
                    if int(last_name[:2]) == int(str(seq_year)) and int(last_name[2:4]) == int(str(seq_month)) and int(last_name[4:6]) == int(str(seq_day)) and last_name[6:8] == str(seq_number):
                        seq_qty = int(last_name[8:11])
                    if len(str(seq_month)) == 1:
                        seq_month = '0' + str(seq_month)
                    if len(str(seq_day)) == 1:
                        seq_day = '0' + str(seq_day)
                    seq_values = '%s%s%s%s%s' % (seq_year, seq_month, seq_day, seq_number, str(int((seq_qty) + 1)).zfill(3))
                else:
                    if len(str(seq_month)) == 1:
                        seq_month = '0' + str(seq_month)
                    if len(str(seq_day)) == 1:
                        seq_day = '0' + str(seq_day)
                    seq_values = '%s%s%s%s%s' % (seq_year, seq_month, seq_day, seq_number, str(int(seq_qty)).zfill(3))

                vals['name'] = seq_values

        return super().create(vals_list)


    def _prepare_confirmation_values(self):
        """ Prepare the sales order confirmation values.

        Note: self can contain multiple records.

        :return: Sales Order confirmation values
        :rtype: dict
        """
        return {
            'state': 'sale',
            #'date_order': fields.Datetime.now()
        }


    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        bank_id = False
        for bnk in self.company_id.partner_id.bank_ids:
            if bnk.acc_number == '5002411886':
                bank_id = bnk.id

        values = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.partner_invoice_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'partner_type_id': self.partner_type.id,
            'payment_reference': self.reference,
            'transaction_ids': [Command.set(self.transaction_ids.ids)],
            'company_id': self.company_id.id,
            'partner_bank_id':bank_id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
        }
        if self.journal_id:
            values['journal_id'] = self.journal_id.id
        return values


    @api.depends('partner_id')
    def _compute_partner_type(self):
        for order in self:
            order = order.with_company(order.company_id)
            partner_type_id = self.env['partner.type.register'].search([('partner_type', '=', order.partner_id.partner_type),('company_id','=',order.company_id.id)], limit=1)
            order.partner_type = partner_type_id.id

    def _compute_contract(self):
        for sale in self:
            contracts = self.env['sales.contract.register'].search([('sales_ids', 'in', (sale.id))])
            sale.contract_id = contracts
            sale.contract_count = len(contracts)


    def create_sale_contract(self):
        sales_contract = self.env['sales.contract.register'].search([('partner_id', '=', self.partner_id.id),('sales_ids', 'in', (self.id))])
        if sales_contract:
            raise UserError('Contract already exists')
        elif self.amount_total == 0:
            raise UserError('Amount total is 0')
        else:
            self.env['sales.contract.register'].create({
                'partner_id': self.partner_id.id,
                'sales_manager_id': self.user_id.id,
                'sales_team_id': self.team_id.id,
                'sales_ids': [(4, self.id)],
                'contract_amount': self.amount_total,
                'currency_id': self.currency_id.id,
                'name': '/',
                'state': 'draft',
                'start_date': self.date_order,
                'end_date': self.date_order,
            })


class SaleOrderLine(models.Model):
    """Inherits the model sale.order.line to add a field"""
    _inherit = 'sale.order.line'

    order_line_image = fields.Binary(string="Image",
                                     compute='_compute_product_image',
                                     readonly=False, 
                                     precompute=True,
                                     store=True)
    unit_price = fields.Float(string='Unit Price',
                              compute='_compute_product_standard_price',                
                              store=True,  
                              digits='Product Price')
    add_desc = fields.Text(string='Add Description')
    request_line_id = fields.Many2one('purchase.requisition.line', string='Request line')



    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.product_uom_qty,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [Command.set(self.tax_id.ids)],
            'sale_line_ids': [Command.link(self.id)],
            'is_downpayment': self.is_downpayment,
        }
        analytic_account_id = self.order_id.analytic_account_id.id
        if self.analytic_distribution and not self.display_type:
            res['analytic_distribution'] = self.analytic_distribution
        if analytic_account_id and not self.display_type:
            analytic_account_id = str(analytic_account_id)
            if 'analytic_distribution' in res:
                res['analytic_distribution'][analytic_account_id] = res['analytic_distribution'].get(analytic_account_id, 0) + 100
            else:
                res['analytic_distribution'] = {analytic_account_id: 100}
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res



    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            if line.price_unit == 0.0:
                if line.qty_invoiced > 0:
                    continue
                if not line.product_uom or not line.product_id:
                    line.price_unit = 0.0
                else:
                    price = line.with_company(line.company_id)._get_display_price()
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                        line.company_id or line.env.company,
                        line.order_id.currency_id,
                        line.order_id.date_order,
                        'sale',
                        fiscal_position=line.order_id.fiscal_position_id,
                        product_price_unit=price,
                        product_currency=line.currency_id
                    )

    @api.depends('product_id')
    def _compute_product_image(self):
        for line in self:
            if not line.order_line_image or (line.product_id.image_1920 != line.order_line_image):
                line.order_line_image = line.product_id.image_1920
        

    @api.depends('product_id')
    def _compute_product_standard_price(self):
        for line in self:
            if line.product_id:
                line.unit_price = line.product_id.standard_price
                
    