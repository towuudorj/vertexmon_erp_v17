# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *
import logging
from pytz import timezone
from dateutil import parser

_logger = logging.getLogger(__name__)


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


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    sharepoint_id = fields.Integer("Share Point ID")

    @api.model
    def default_get(self, fields):
        result = super(HrExpense, self).default_get(fields)
        if 'product_id' in fields:
            expense_product = self.env['product.product'].search([('description', 'ilike', 'expense')])
            if expense_product:
                result['product_id'] = expense_product[0].id
        return result


    def get_approved_expense(self):
        microsoft_value_obj = self.env['microsoft.api.value'].sudo().search([], limit=1)
        token = get_token(microsoft_value_obj)
        if token['token_type'] and token['access_token']:
            token = token['token_type'] + ' ' + token['access_token']
        else:
            raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(token))

        site_id = get_site_id(microsoft_value_obj, token)

        list_id = get_list_id(microsoft_value_obj, site_id, token, 'payment_list_name', 'payment_list_id')

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$expand=fields"
        headers = {
            "Authorization": token,
        }
        response = requests.get(url, headers=headers, json={})
        response_json = response.json()
        expense_obj = self.env['hr.expense'].sudo()
        hr_expense_ids = expense_obj.search(['&', ('sharepoint_id', '!=', False), ('sharepoint_id', '!=', '')])
        sharepoint_ids = hr_expense_ids.mapped('sharepoint_id')

        for expense in response_json['value']:
            try:
                data = expense.get('fields', {})
                if data['status'] == 'Батлагдсан' and 'id' in data and int(data['id']) not in sharepoint_ids:

                    tz = timezone('Asia/Ulaanbaatar')
                    request_date = data['request_date']
                    request_date = parser.isoparse(request_date).astimezone(tz)

                    currency_id = self.env['res.currency'].search([('name', '=', data['currency'])], limit=1)
                    account_id = False
                    if 'bank_account' in data:
                        account_id = int(data.get('bank_account'))

                    line_vals = {
                        'name': data['order_numner'],
                        'total_amount_currency': data['amount'],
                        'date': request_date.date(),
                        'employee_id': int(data['created_employee_id']) if 'created_employee_id' in data else 1,
                        'currency_id': currency_id.id if currency_id else False,
                        'company_id': int(data['odoo_company_id']),
                        'sharepoint_id': int(data['id'])
                    }

                    expense_vals = {
                        'name': data['order_numner'],
                        'accounting_date': request_date.date(),
                        'partner_id': data['partner_name'],
                        'bank_account_id': account_id,
                        'company_id': int(data['odoo_company_id']),
                        'employee_id': int(data['created_employee_id']) if 'created_employee_id' in data else 1,
                        'expense_line_ids': [(0, 0, line_vals)],
                    }
                    self.env['hr.expense.sheet'].sudo().create(expense_vals)
            except Exception as e:
                _logger.error(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(e))

    
class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    bank_account_id = fields.Many2one('res.partner.bank',string='Bank account')
    amount_text = fields.Char(string='Amount in words', compute='_compute_amount_text')
    currency_id = fields.Many2one('res.currency', string='Currency')
    currency_amount = fields.Float(string='Currency amount', compute='_compute_currency_amount')
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    accounting_date = fields.Date(string="Accounting Date", compute='_compute_accounting_date',
                                  default=fields.Date.context_today,  store=True)


    def _compute_currency_amount(self):
        for record in self:
            currency_amount = 0
            currency_id = False
            for line in record.expense_line_ids:
                currency_amount = line.total_amount_currency
                currency_id = line.currency_id
            record.currency_amount = currency_amount
            record.currency_id = currency_id

    @api.depends('total_amount')
    def _compute_amount_text(self):
        for record in self:
            if record.total_amount:
                currency_amount = 0
                for line in record.expense_line_ids:
                    currency_amount = line.total_amount_currency
                if currency_amount > 0:
                    record.amount_text = verbose_format(currency_amount,record.currency_id)
                else:
                    record.amount_text = verbose_format(record.total_amount,record.currency_id)
            else:
                record.amount_text = ''