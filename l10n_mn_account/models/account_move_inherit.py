# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from collections import defaultdict
from contextlib import contextmanager
from odoo.tools import float_is_zero
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.tools import frozendict, format_date, float_compare, Query


def verbose_format(amount,currency):
    u'''Мөнгөн дүнг үсгээр илэрхийлэх функц
    '''
    amount = str(amount)
    result = u''
    BUTARHAI = True
    i = 0
    stramount = amount.replace(',','.')
    
    if '-' in stramount:
        stramount= stramount.replace('-','')        
    if '.' in amount:
        amount = stramount[:stramount.find('.')]
        subamount = stramount[stramount.find('.')+1:]
    else :
        amount = stramount
        subamount = u''
    length = len(amount)
    if length == 0 or float(amount) == 0:
        return ''
    place = 0
    try :
        while i < length :
            c = length - i
            if c % 3 == 0 :
                c -= 3
            else :
                while c % 3 != 0 :
                    c -= 1
            place = c / 3
            i1 = length - c
            tmp = amount[i:i1]
            j = 0
            if tmp == '000' :
                i = i1
                continue
            while j < len(tmp) :
                char = int(tmp[j])
                p = len(tmp) - j
                if char == 1 :
                    if p == 3 :
                        result += u'нэг зуун '
                    elif p == 2 :
                        result += u'арван '
                    elif p == 1 :
                        if len(result)==0:
                            result += u'нэг '
                        else:
                            result += u'нэгэн '
                elif char == 2 :
                    if p == 3 :
                        result += u'хоёр зуун '
                    elif p == 2 :
                        result += u'хорин '
                    elif p == 1 :
                        result += u'хоёр '
                elif char == 3 :
                    if p == 3 :
                        result += u'гурван зуун '
                    elif p == 2 :
                        result += u'гучин '
                    elif p == 1 :
                        result += u'гурван '
                elif char == 4 :
                    if p == 3 :
                        result += u'дөрвөн зуун '
                    elif p == 2 :
                        result += u'дөчин '
                    elif p == 1 :
                        result += u'дөрвөн '
                elif char == 5 :
                    if p == 3 :
                        result += u'таван зуун '
                    elif p == 2 :
                        result += u'тавин '
                    elif p == 1 :
                        result += u'таван '
                elif char == 6 :
                    if p == 3 :
                        result += u'зургаан зуун ' 
                    elif p == 2 :
                        result += u'жаран '
                    elif p == 1 :
                        result += u'зургаан '
                elif char == 7 :
                    if p == 3 :
                        result += u'долоон зуун '
                    elif p == 2 :
                        result += u'далан '
                    elif p == 1 :
                        result += u'долоон '
                elif char == 8 :
                    if p == 3 :
                        result += u'найман зуун '
                    elif p == 2 :
                        result += u'наян '
                    elif p == 1 :
                        result += u'найман '
                elif char == 9 :
                    if p == 3 :
                        result += u'есөн зуун '
                    elif p == 2 :
                        result += u'ерэн '
                    elif p == 1 :
                        result += u'есөн '
                
                j += 1
            # -------- end while j < len(tmp)
            if place == 3 :
                result += u'тэрбум '
            elif place == 2 :
                result += u'сая '
            elif place == 1 :
                result += u'мянга '
            i = i1
        # ---------- end while i < len(amount)
    except Exception :
        return False
    
    if len(subamount) > 0 and float(subamount) > 0 :
        result2 = verbose_format(subamount,currency)
        BUTARHAI = False
        if currency.name == 'MNT':
            result2 = result2.replace(u'төгрөг', u'мөнгө')
            result += u' төгрөг %s' % result2
        if currency.name == 'USD':
            result2 = result2.replace(u'ам доллар', u'цент')
            result += u' ам доллар %s' % result2
        if currency.name == 'EUR':
            result2 = result2.replace(u'евро', u'цент')
            result += u' евро %s' % result2
    if BUTARHAI:
        if currency.name == 'MNT':
            result += u' төгрөг'
        if currency.name == 'USD':
            result += u' ам доллар'
            
        if currency.name == 'EUR':
            result += u' евро'

    num = result
    if currency.name == 'MNT':
        if u"мянга  төгрөг" in num:
            result = num.replace(u"мянга  төгрөг",u"мянган  төгрөг")
        else:
            result = num
    elif currency.name == 'USD':
        if u"ам доллар" in num:
            result = num.replace(u"ам доллар",u" ам доллар")
        else:
            result = num
    elif currency.name == 'EUR':
        if u"евро" in num:
            result = num.replace(u" евро",u" евро")
        else:
            result = num
            
    return result


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    amount_text = fields.Char(string='Amount text',
         readonly=True,compute='_compute_amount')
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        compute='_compute_journal_id', inverse='_inverse_journal_id', store=True, readonly=False, precompute=True,
        required=True,
        check_company=True,
        domain="[('id', 'in', suitable_journal_ids)]",
    )
    partner_type_id = fields.Many2one('partner.type.register', string='Partner type')
    po_ids = fields.Many2many('purchase.order', string='Purchase Orders', domain="[('state', '=', 'purchase')]")
    invoice_date_due = fields.Date(string='Төлбөр хийх хугацаа', readonly=True)
    vat_declaration = fields.Char(string='VAT Declaration')
    advance_payment_percentage = fields.Float(string='Advance Payment Percentage')
    is_advance_payment = fields.Boolean(string='Advance Payment')
    advance_payment_amount = fields.Monetary(string="Advance Payment Amount", compute="_compute_advance_payment_amount")
    invoice_state = fields.Selection([('parent_approve', 'Parent approve'), ('accountant_approve', 'Accountant approve')],
                                     default='parent_approve')
    invisible_approve_to_parent = fields.Boolean(compute='_compute_invisible_approve_to_parent')
    parent_notif_sent = fields.Boolean(default=False)


    def approve_to_accountant(self):
        job_obj = self.env['hr.job'].sudo()
        for obj in self:
            if obj.invoice_state == 'parent_approve':
                job_id = job_obj.search([('name', 'ilike', 'нягтлан бодогч'), ('name', '!=', 'Тооцооны нягтлан бодогч')])
                head = False
                if job_id:
                    accountants = self.env['hr.employee'].search([('job_id', 'in', job_id.ids), ('company_id', '=', obj.company_id.id)], order='create_date asc')
                    if accountants:
                        acc_move_url = f'/web#id={self.id}&model=account.move&view_type=form'
                        self.env['mail.mail'].create({
                            'email_to': ', '.join(accountants.mapped('work_email')),
                            'subject': f'Нэхэмжлэл батлах хүсэлт ирлээ.',
                            'body_html': f"""Таньд нэхэмжлэл батлах хүсэлт ирлээ..<br><br>
                                             <a href="{acc_move_url}"
                                             style="border-image-repeat:stretch;border-image-outset:0;border-image-width:1;border-image-slice:100%;border-image-source:none;border-style:solid;
                                                    box-sizing:border-box;border-left-color:#875a7b;border-bottom-color:#875a7b;border-right-color:#875a7b;border-top-color:#875a7b;border-left-width:1px;
                                                    border-bottom-width:1px;border-right-width:1px;border-top-width:1px;padding: 5px 10px; color: #FFFFFF; text-decoration: none; background-color: #875A7B; border: 1px solid #875A7B; border-radius: 3px">
                                     Нэхэмжлэл</a><br>
                                         """
                        }).send()
                obj.invoice_state = 'accountant_approve'

    def action_send_parent_notif(self):
        for obj in self:
            parent_email = obj.create_uid.employee_id.parent_id.work_email
            if parent_email:
                acc_move_url = f'/web#id={self.id}&model=account.move&view_type=form'
                self.env['mail.mail'].create({
                    'email_to': parent_email,
                    'subject': f'Нэхэмжлэл батлах хүсэлт ирлээ.',
                    'body_html': f"""Таньд нэхэмжлэл батлах хүсэлт ирлээ.<br><br>
                                     <a href="{acc_move_url}"
                                             style="border-image-repeat:stretch;border-image-outset:0;border-image-width:1;border-image-slice:100%;border-image-source:none;border-style:solid;
                                                    box-sizing:border-box;border-left-color:#875a7b;border-bottom-color:#875a7b;border-right-color:#875a7b;border-top-color:#875a7b;border-left-width:1px;
                                                    border-bottom-width:1px;border-right-width:1px;border-top-width:1px;padding: 5px 10px; color: #FFFFFF; text-decoration: none; background-color: #875A7B; border: 1px solid #875A7B; border-radius: 3px">
                                     Нэхэмжлэл</a><br>
                                 """
                }).send()
                obj.parent_notif_sent = True
        return

    @api.depends('date', 'auto_post')
    def _compute_hide_post_button(self):
        for record in self:
            if record.move_type != 'entry':
                record.hide_post_button = record.invoice_state != 'accountant_approve' or record.state != 'draft' \
                    or record.auto_post != 'no' and record.date > fields.Date.context_today(record)
            else:
                record.hide_post_button = record.state != 'draft' \
                    or record.auto_post != 'no' and record.date > fields.Date.context_today(record)

    def _compute_invisible_approve_to_parent(self):
        current_user = self.env.user
        for obj in self:
            obj.invisible_approve_to_parent = obj.create_uid.employee_id.parent_id.id != current_user.employee_id.id

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        ''' Prepare values used to create the journal items (account.move.line) corresponding to the Cost of Good Sold
        lines (COGS) for customer invoices.

        Example:

        Buy a product having a cost of 9 being a storable product and having a perpetual valuation in FIFO.
        Sell this product at a price of 10. The customer invoice's journal entries looks like:

        Account                                     | Debit | Credit
        ---------------------------------------------------------------
        200000 Product Sales                        |       | 10.0
        ---------------------------------------------------------------
        101200 Account Receivable                   | 10.0  |
        ---------------------------------------------------------------

        This method computes values used to make two additional journal items:

        ---------------------------------------------------------------
        220000 Expenses                             | 9.0   |
        ---------------------------------------------------------------
        101130 Stock Interim Account (Delivered)    |       | 9.0
        ---------------------------------------------------------------

        Note: COGS are only generated for customer invoices except refund made to cancel an invoice.

        :return: A list of Python dictionary to be passed to env['account.move.line'].create.
        '''
        lines_vals_list = []
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        for move in self:
            # Make the loop multi-company safe when accessing models like product.product
            move = move.with_company(move.company_id)

            if not move.is_sale_document(include_receipts=True) or not move.company_id.anglo_saxon_accounting:
                continue

            for line in move.invoice_line_ids:

                # Filter out lines being not eligible for COGS.
                if not line._eligible_for_cogs():
                    continue

                # Retrieve accounts needed to generate the COGS.
                accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)
                debit_interim_account = accounts['stock_output']
                credit_expense_account = accounts['expense'] or move.journal_id.default_account_id
                if not debit_interim_account or not credit_expense_account:
                    continue

                # Compute accounting fields.
                sign = -1 if move.move_type == 'out_refund' else 1
                price_unit = line._stock_account_get_anglo_saxon_price_unit()
                amount_currency = sign * line.quantity * price_unit

                if move.currency_id.is_zero(amount_currency) or float_is_zero(price_unit, precision_digits=price_unit_prec):
                    continue

                # Add interim account line.
                lines_vals_list.append({
                    'name': line.name[:64],
                    'move_id': move.id,
                    'partner_id': move.commercial_partner_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': price_unit,
                    'amount_currency': -amount_currency,
                    'account_id': debit_interim_account.id,
                    'display_type': 'cogs',
                    'tax_ids': [],
                    'cogs_origin_id': line.id,
                })

                # Add expense account line.
                lines_vals_list.append({
                    'name': line.name[:64],
                    'move_id': move.id,
                    'partner_id': move.commercial_partner_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': -price_unit,
                    'amount_currency': amount_currency,
                    'account_id': credit_expense_account.id,
                    'analytic_distribution': line.analytic_distribution,
                    'display_type': 'cogs',
                    'tax_ids': [],
                    'cogs_origin_id': line.id,
                })
        return lines_vals_list

    @api.depends('advance_payment_percentage', 'amount_total')
    def _compute_advance_payment_amount(self):
        for record in self:
            if record.advance_payment_percentage:
                record.advance_payment_amount = ((record.amount_total / (record.advance_payment_percentage)) * 100.0)
            else:
                record.advance_payment_amount = 0.0    


    @api.depends('bank_partner_id')
    def _compute_partner_bank_id(self):
        for move in self:
            bank_id = False
            bank_ids = move.bank_partner_id.bank_ids.filtered(
                lambda bank: not bank.company_id or bank.company_id == move.company_id)
            for bnk in bank_ids:
                if bnk.acc_number == '5002411886':
                    bank_id = bnk.id
            move.partner_bank_id = bank_id

    def button_create_landed_costs(self):
        """Create a `stock.landed.cost` record associated to the account move of `self`, each
        `stock.landed.costs` lines mirroring the current `account.move.line` of self.
        """
        self.ensure_one()
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)

        landed_costs = self.env['stock.landed.cost'].create({
            'vendor_bill_id': self.id,
            'po_ids': [(6, 0, self.po_ids.ids)],
            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'account_id': l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
                'price_unit': l.currency_id._convert(l.price_subtotal, l.company_currency_id, l.company_id, l.move_id.date),
                'split_method': l.product_id.split_method_landed_cost or 'equal',
            }) for l in landed_costs_lines],
        })
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self = self.with_company(self.journal_id.company_id._accessible_branches()[:1])

        warning = {}
        if self.partner_id:
            rec_account = self.partner_id.property_account_receivable_id
            pay_account = self.partner_id.property_account_payable_id
            self.partner_type_id = self.partner_id.partner_type.id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            p = self.partner_id
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn and p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s", p.name),
                    'message': p.invoice_warn_msg
                }
                if p.invoice_warn == 'block':
                    self.partner_id = False
                return {'warning': warning}


    @api.depends('move_type')
    def _compute_journal_id(self):
        for record in self.filtered(lambda r: r.journal_id.type not in r._get_valid_journal_types()):
            record.journal_id = record._search_default_journal()


    def _get_valid_journal_types(self):
        if self.is_sale_document(include_receipts=True):
            return ['sale']
        elif self.is_purchase_document(include_receipts=True):
            return ['purchase']
        elif self.payment_id or self.env.context.get('is_payment'):
            return ['bank', 'cash']
        return ['general','opening']
    

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            if m.invoice_filter_type_domain:
                journal_type = m.invoice_filter_type_domain or ['general', 'opening']
                company = m.company_id or self.env.company
                
                m.suitable_journal_ids = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', journal_type),
                ])
            else:
                journal_type = m.invoice_filter_type_domain or ['general', 'opening']
                company = m.company_id or self.env.company
                
                m.suitable_journal_ids = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', 'in', journal_type),
                ])
    
    
    
    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'state')
    def _compute_amount(self):
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding'):
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign
            to_text = verbose_format(move.amount_total,move.currency_id)
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)
            move.amount_text = to_text.capitalize()
            

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    cash_move_type_id = fields.Many2one('account.cash.move.type', string='Cash Move Type')
    country_origin = fields.Many2one('res.country', string='Country of Origin')
    counterpart_account_name = fields.Char(string='Counterpart Account', compute='_compute_counterpart_account_name',
                                           store=True)


    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_field_values = {}
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        amount = 0
        for account in self.env['account.analytic.account'].browse(map(int, account_ids.split(","))):
            distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
                amount = -self.balance * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
            else:
                amount = -self.balance * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        month = False
        if self.month:
            month = self.month

        return {
            'name': default_name,
            'date': self.date,
            **account_field_values,
            'partner_id': self.partner_id.id,
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'month':month,
            'move_line_id': self.id,
            'user_id': self.move_id.invoice_user_id.id or self._uid,
            'company_id': self.company_id.id or self.env.company.id,
            'category': 'invoice' if self.move_id.is_sale_document() else 'vendor_bill' if self.move_id.is_purchase_document() else 'other',
        }


    @contextmanager
    def _sync_invoice(self, container):
        if container['records'].env.context.get('skip_invoice_line_sync'):
            yield
            return  # avoid infinite recursion

        def existing():
            return {
                line: {
                    'amount_currency': line.currency_id.round(line.amount_currency),
                    'balance': line.company_id.currency_id.round(line.balance),
                    'currency_rate': line.currency_rate,
                    'price_subtotal': line.currency_id.round(line.price_subtotal),
                    'move_type': line.move_id.move_type,
                } for line in container['records'].with_context(
                    skip_invoice_line_sync=True,
                ).filtered(lambda l: l.move_id.is_invoice(True))
            }

        def changed(fname):
            return line not in before or before[line][fname] != after[line][fname]

        before = existing()
        yield
        after = existing()
        for line in after:
            if (
                line.display_type == 'product'
                and (not changed('amount_currency') or line not in before)
            ):
                amount_currency = line.move_id.direction_sign * line.currency_id.round(line.price_subtotal)
                if line.amount_currency != amount_currency or line not in before:
                    line.amount_currency = amount_currency
                if line.currency_id == line.company_id.currency_id:
                    line.balance = amount_currency

        after = existing()
        for line in after:
            if (
                (changed('amount_currency') or changed('currency_rate') or changed('move_type'))
                and (not changed('balance') or (line not in before and not line.balance))
            ):
                balance = line.company_id.currency_id.round(line.amount_currency * line.currency_rate)
                line.balance = balance
        # Since this method is called during the sync, inside of `create`/`write`, these fields
        # already have been computed and marked as so. But this method should re-trigger it since
        # it changes the dependencies.
        self.env.add_to_compute(self._fields['debit'], container['records'])
        self.env.add_to_compute(self._fields['credit'], container['records'])


    @api.depends('currency_id', 'company_id', 'move_id.date')
    def _compute_currency_rate(self):
        for line in self:
            if line.currency_id:
                rate = self.env['res.currency']._get_conversion_rate(
                    
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line),
                )
                line.currency_rate = round(1/rate,2)
                
            else:
                line.currency_rate = 1

    @api.depends('move_id.line_ids', 'move_id.line_ids.account_id', 'account_id')
    def _compute_counterpart_account_name(self):
        for line in self:
            if not line.move_id:
                line.counterpart_account_name = False
                continue
            counterpart_lines = line.move_id.line_ids.filtered(lambda l: l.id != line.id)
            counterpart_name = ', '.join(l.code + ' ' + l.name
                for l in counterpart_lines.mapped('account_id')
            )
            line.counterpart_account_name = counterpart_name