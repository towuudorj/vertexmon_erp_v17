# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from collections import defaultdict
from contextlib import contextmanager
from odoo.tools import float_is_zero
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.tools import frozendict, format_date, float_compare, Query
from markupsafe import Markup


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
    # Тусдаа relation хүснэгт: өгөгдмөл нэр (account_move_purchase_order_rel) нь purchase.order.invoice_ids-тэй
    # давхцаж, PO-ийн invoice_ids дахин тооцоологдох бүрт гараар оруулсан Баримтын дугаар устдаг байсан.
    po_ids = fields.Many2many('purchase.order', 'account_move_po_ids_rel', 'move_id', 'purchase_order_id',
                              string='Purchase Orders', domain="[('state', '=', 'purchase')]",
                              compute='_compute_po_ids', store=True, readonly=False, copy=True)
    has_landed_costs = fields.Boolean(compute='_compute_has_landed_costs')
    invoice_date_due = fields.Date(string='Төлбөр хийх хугацаа', readonly=True)
    vat_declaration = fields.Char(string='VAT Declaration')
    advance_payment_percentage = fields.Float(string='Advance Payment Percentage')
    is_advance_payment = fields.Boolean(string='Advance Payment')
    advance_payment_amount = fields.Monetary(string="Advance Payment Amount", compute="_compute_advance_payment_amount")
    invoice_state = fields.Selection([('parent_approve', 'Parent approve'), ('accountant_approve', 'Accountant approve')],
                                     default='parent_approve')
    invisible_approve_to_parent = fields.Boolean(compute='_compute_invisible_approve_to_parent')
    parent_notif_sent = fields.Boolean(default=False)

    @api.depends('invoice_line_ids.purchase_line_id')
    def _compute_po_ids(self):
        # Худалдан авалтаас үүссэн нэхэмжлэлийн PO-г нэмнэ, гараар оруулсныг хэвээр үлдээнэ
        for move in self:
            move.po_ids |= move.invoice_line_ids.purchase_line_id.order_id

    def write(self, vals):
        current_po_id_dict = {}
        if 'po_ids' in vals:
            for obj in self:
                current_po_id_dict[obj.id] = obj.po_ids

        res = super(AccountMove, self).write(vals)

        if 'po_ids' in vals:
            for obj in self:
                current_po_ids = current_po_id_dict.get(obj.id)
                new_po_ids = obj.po_ids
                obj.message_post(
                    body=Markup(f"""
                        <p><strong>Баримтын дугаар: </strong> ({', '.join(po.display_name for po in current_po_ids)}) -> ({', '.join(po.display_name for po in new_po_ids)})</p>
                    """),
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )
        return res


    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)
        if 'po_ids' in vals:
            for obj in res:
                new_po_ids = obj.po_ids
                obj.message_post(
                    body=Markup(f"""
                        <p><strong>Баримтын дугаар: </strong> () -> ({', '.join(po.display_name for po in new_po_ids)})</p>
                    """),
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )
        return res


    def approve_to_accountant(self):
        job_obj = self.env['hr.job'].sudo()
        for obj in self:
            if obj.invoice_state == 'parent_approve':
                job_id = job_obj.search([('name', 'ilike', 'нягтлан бодогч')])
                if job_id:
                    accountants = self.env['hr.employee'].search([('job_id', 'in', job_id.ids),
                                                                  ('company_id', '=', obj.company_id.id),
                                                                  ('work_email', '!=', False)
                                                                 ], order='create_date asc')
                    if accountants and accountants.mapped('work_email'):
                        acc_move_url = f'/web#id={obj.id}&model=account.move&view_type=form'
                        self.env['mail.mail'].create_notification(
                            email_to=', '.join(accountants.mapped('work_email')),
                            subject=f"{'Нийлүүлэгчийн' if obj.move_type == 'in_invoice' else 'Захиалагчийн'} нэхэмжлэл батлах хүсэлт ирлээ.",
                            intro='Таньд нэхэмжлэл батлах хүсэлт ирлээ.',
                            details=[
                                ('Харилцагч', obj.partner_id.name or ''),
                                ('Нэхэмжлэлийн дүн', f'{obj.amount_total:,.2f}'),
                            ],
                            url=acc_move_url,
                            link_label='Нэхэмжлэл',
                        )
                obj.invoice_state = 'accountant_approve'
                obj.message_post(
                    body=Markup("""
                        <p><strong>Шууд удирдлага хянав.</strong></p>
                    """),
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )

    def action_send_parent_notif(self):
        job_obj = self.env['hr.job'].sudo()
        for obj in self:
            email = False
            if obj.move_type == 'in_invoice':
                email = obj.create_uid.employee_id.parent_id.work_email
            elif obj.move_type == 'out_invoice':
                job_id = job_obj.search([('name', 'ilike', 'нягтлан бодогч')])
                if job_id:
                    accountants = self.env['hr.employee'].search(
                        [('job_id', 'in', job_id.ids), ('company_id', '=', obj.company_id.id)], order='create_date asc')
                    email = ', '.join(accountants.mapped('work_email'))
            if email:
                acc_move_url = f'/web#id={self.id}&model=account.move&view_type=form'
                self.env['mail.mail'].create_notification(
                    email_to=email,
                    subject=f"{'Нийлүүлэгчийн' if obj.move_type == 'in_invoice' else 'Захиалагчийн'} нэхэмжлэл {'хянах' if obj.move_type == 'in_invoice' else 'батлах'} хүсэлт ирлээ.",
                    intro=f"Таньд нэхэмжлэл {'хянах' if obj.move_type == 'in_invoice' else 'батлах'} хүсэлт ирлээ.",
                    details=[
                        ('Харилцагч', obj.partner_id.name),
                        ('Нэхэмжлэлийн дүн', f'{obj.amount_total:,.2f}'),
                    ],
                    url=acc_move_url,
                    link_label='Нэхэмжлэл',
                )
                obj.parent_notif_sent = True
        return

    def _compute_invisible_approve_to_parent(self):
        current_user = self.env.user
        for obj in self:
            obj.invisible_approve_to_parent = obj.create_uid.employee_id.parent_id.id != current_user.employee_id.id or obj.move_type != 'in_invoice'

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

    def _compute_has_landed_costs(self):
        # Агуулахын эрхгүй хэрэглэгч нэхэмжлэл нээхэд stock.landed.cost-ийн эрхийн алдаа гаргахгүйн тулд sudo
        for move in self:
            move.has_landed_costs = 'landed_costs_ids' in move._fields and bool(move.sudo().landed_costs_ids)

    def _get_missing_product_lines(self):
        """Бараа сонгоогүй нэхэмжлэлийн мөрүүд (татвар, хэсэг, тэмдэглэлийн мөр орохгүй)."""
        return self.filtered(lambda m: m.is_invoice(include_receipts=True)).invoice_line_ids.filtered(
            lambda line: line.display_type == 'product' and not line.product_id)

    def action_post(self):
        # Зөвхөн хэрэглэгч "Батлах" товч дарахад (check_missing_product) шалгана;
        # кодоор батлах автомат урсгалд (төлбөрийн нөхцөлийн нэхэмжлэл г.м.) нөлөөлөхгүй.
        if self.env.context.get('check_missing_product') and self._get_missing_product_lines():
            wizard = self.env['account.move.missing.product.confirm'].create({'move_ids': [(6, 0, self.ids)]})
            return {
                'name': _('Бараа сонгоогүй мөр байна'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move.missing.product.confirm',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
                # Вэб клиент товчны context-ийг (check_missing_product=True) нэгтгэдэг тул тодорхой False болгоно
                'context': dict(self.env.context, check_missing_product=False),
            }
        # Дотор нь бусад бичилт батлагдахад дахин шалгахгүй
        return super(AccountMove, self.with_context(check_missing_product=False)).action_post()

    def _check_receivable_payable_partner(self):
        """Авлага, өглөгийн данстай журналын мөрөнд харилцагч заавал сонгогдсон байх ёстой.
        Дансан дээр "Харилцагч заавал биш" сонгосон бол тухайн дансны мөрийг шалгахгүй."""
        # Харилцагчийн үлдэгдэл шилжүүлэх wizard (ахлах нягтлан) харилцагчгүй мөр рүү төвлөрүүлэхэд л алгасна
        if self._context.get('skip_receivable_payable_partner_check'):
            return
        for move in self:
            lines = move.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                and not l.account_id.partner_not_required
                and not l.partner_id)
            if lines:
                raise UserError(_(
                    "Авлага, өглөгийн данс сонгосон мөрөнд харилцагч заавал сонгоно уу!\n"
                    "Баримт: %(move)s\nДанс: %(accounts)s",
                    move=move.display_name,
                    accounts=', '.join(lines.mapped('account_id.display_name')),
                ))

    def _post(self, soft=True):
        self.filtered(lambda m: m.state == 'draft' or not soft)._check_receivable_payable_partner()
        return super()._post(soft=soft)

    def button_create_landed_costs(self):
        """Create a `stock.landed.cost` record associated to the account move of `self`, each
        `stock.landed.costs` lines mirroring the current `account.move.line` of self.
        """
        self.ensure_one()
        if not self.po_ids:
            raise ValidationError(u"Баримтын дугаар бүртгэгдээгүй байна!")
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
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)
            to_text = verbose_format(move.amount_total,move.currency_id)
            move.amount_text = to_text.capitalize()

    def _get_report_base_filename(self):
        if self.move_type in ['in_invoice', 'out_invoice']:
            analytic_account_ids = []
            for line in self.invoice_line_ids:
                if line.analytic_distribution:
                    analytic_account_ids += list(line.analytic_distribution.keys())
            if len(analytic_account_ids) == 1:
                analytic_account = self.env['account.analytic.account'].browse(int(analytic_account_ids[0]))
                project = analytic_account.project_ids[0]
                name = ''
                name += {
                    'out_invoice': _('Invoice %s' % project.name),
                    'in_invoice': _('Bill %s' % project.name),
                }[self.move_type]
                if not self.name or self.name == '/':
                    if self.id:
                        name += '(* %s)' % str(self.id)
                else:
                    name += self.name
                return name
        return super(AccountMove, self)._get_report_base_filename()

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    cash_move_type_id = fields.Many2one('account.cash.move.type', string='Cash Move Type')
    country_origin = fields.Many2one('res.country', string='Country of Origin')
    counterpart_account_name = fields.Char(string='Counterpart Account', compute='_compute_counterpart_account_name',
                                           store=True)
    is_liquidity_counterpart = fields.Boolean(
        string='Хуулгын харьцсан тал нь мөнгөн данс', compute='_compute_is_liquidity_counterpart',
        search='_search_is_liquidity_counterpart',
        help='Банкны хуулгын бичилтэд журналын үндсэн данснаас өөр мөнгөн хөрөнгийн (банк, касс) дансны мөр. '
             'Данс хоорондын шилжүүлгийг дамжин өнгөрөх дансаар биш шууд нөгөө банкны дансаар тулгасныг илтгэнэ.')

    def _compute_is_liquidity_counterpart(self):
        for line in self:
            line.is_liquidity_counterpart = bool(
                line.move_id.statement_line_id
                and line.account_id.account_type == 'asset_cash'
                and line.account_id != line.move_id.journal_id.default_account_id
            )

    def _search_is_liquidity_counterpart(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_('Unsupported operator: %s') % operator)
        self.env.cr.execute("""
            SELECT aml.id
              FROM account_move_line aml
              JOIN account_move am ON am.id = aml.move_id
              JOIN account_journal j ON j.id = am.journal_id
              JOIN account_account aa ON aa.id = aml.account_id
             WHERE am.statement_line_id IS NOT NULL
               AND aa.account_type = 'asset_cash'
               AND aml.account_id IS DISTINCT FROM j.default_account_id
        """)
        ids = [r[0] for r in self.env.cr.fetchall()]
        positive = (operator == '=') == bool(value)
        return [('id', 'in' if positive else 'not in', ids)]


    def write(self, vals):
        res = super().write(vals)
        # Журналын бичилтээс мөнгөний мөрийн төрлийг засвал банкны хуулгын мөрт буцааж дамжуулна
        if 'cash_move_type_id' in vals and not self._context.get('skip_cash_move_type_sync'):
            for st_line in self.move_id.statement_line_id:
                liquidity_lines = st_line._seek_for_lines()[0]
                changed = liquidity_lines & self
                if changed and st_line.cash_move_type_id != changed[0].cash_move_type_id:
                    st_line.with_context(skip_account_move_synchronization=True,
                                         skip_cash_move_type_sync=True).write(
                        {'cash_move_type_id': changed[0].cash_move_type_id.id})
        return res

    def action_clear_non_cash_move_type(self):
        """Мөнгөн хөрөнгийн бус дансны мөрөөс мөнгөн гүйлгээний төрлийг арилгана.
        Мөнгөн дансны мөрүүдийг сонгосон байсан ч хөндөхгүй."""
        lines = self.filtered(lambda l: l.cash_move_type_id and l.account_id.account_type != 'asset_cash')
        lines.write({'cash_move_type_id': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('%s мөрөөс мөнгөн гүйлгээний төрлийг арилгалаа.') % len(lines),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

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