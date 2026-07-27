# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *


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
        # url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
        headers = {
            "Authorization": token,
        }
        print(url, token)
        print(aaaaa)
        response = requests.get(url, headers=headers, json={})
        response_json = response.json()
        print(response_json, '\n\n\n')
        print(aaaaaaa)
        hr_expense_ids = self.env['hr.expense'].sudo().search([('sharepoint_id', '!=', False)])
        sharepoint_ids = hr_expense_ids.mapped('sharepoint_id')
        for expense in response_json:
            fields = {
                'order': 'LinkTitle',
                'name': 'order_numner',
                'partner_odoo_id': 'partner_name',
                'amount': 'amount',
                'request_date': 'request_date',
                'approved_date': 'approved_date',
                'payment_def': 'payment_def',
                'payment_term': 'payment_term',
                'bank_account': 'bank_account',
                'currency': 'currency',
                'add_information': 'add_information',
            }
            try:
                data = expense.get('fields', {})
                if data['status'] == 'approved' and data['id'] and int(data['id']) not in sharepoint_ids:
                    employee = self.env['hr.employee'].search(
                        [('ssnid', '=', data['_x0420__x0435__x0433__x0438__x04'])], limit=1)
                    if data['typeDate'] and data['typeDate'] == 'Цагаар':
                        start_date = data['_x042d__x0445__x043b__x044d__x04']
                        end_date = data['_x0414__x0443__x0443__x0441__x04']
                    else:
                        start_date = data['beginDate']
                        end_date = data['endDate']

                    tz = timezone('Asia/Ulaanbaatar')
                    start_date = parser.isoparse(start_date).astimezone(tz)
                    end_date = parser.isoparse(end_date).astimezone(tz)

                    leave_vals = {
                        'holiday_status_id': payroll_leave_type_id.id if data[
                                                                             'typeSalary'] == 'salary' else unpayroll_leave_type_id.id,
                        'request_unit_hours': True if data['typeDate'] == 'Цагаар' else False,
                        'employee_id': employee.id if employee else False,
                        'sharepoint_id': data['id'],
                    }
                    if data['typeDate'] == 'Цагаар':
                        leave_vals.update(
                            {'request_date_from': str(start_date.date()), 'request_date_to': str(end_date.date()),
                             'request_hour_from': hour_min_to_selection[
                                 str(start_date.hour) + ':' + str(start_date.minute)],
                             'request_hour_to': hour_min_to_selection[str(end_date.hour) + ':' + str(end_date.minute)]
                             })

                    else:
                        leave_vals.update(
                            {'request_date_from': str(start_date.date()), 'request_date_to': str(end_date.date())})
                    leave_obj.create(leave_vals)
            except Exception:
                continue

    
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