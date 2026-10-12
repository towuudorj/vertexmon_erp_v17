# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from odoo import api, fields, models, tools, _
from datetime import date, datetime, time, timedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
               
class ResourceCalendar(models.Model): 
    _inherit = 'resource.calendar'
    
    # is_holiday_time_out = fields.Boolean(string='Holiday time out')
    work_time = fields.Float(string='Working hour')
    lunchtime_start = fields.Float(string='Lunch time start')
    lunchtime_end = fields.Float(string='Lunch time end', compute='_compute_lunchtime_end')

    @api.depends('attendance_ids', 'attendance_ids.hour_from', 'attendance_ids.hour_to', 'two_weeks_calendar')
    def _compute_hours_per_day(self):
        super(ResourceCalendar, self)._compute_hours_per_day()
        for obj in self:
            if obj.work_time:
                obj.hours_per_day = obj.work_time

    @api.onchange('lunchtime_start')
    def _compute_lunchtime_end(self):
        for obj in self:
            if obj.lunchtime_start:
                obj.lunchtime_end = obj.lunchtime_start + 1
            else:
                obj.lunchtime_end = None


class hr_contract(models.Model):
    _inherit = 'hr.contract'
    
    phone_add = fields.Float(string='Phone add')
    administration_add = fields.Float(string='Administration add')
    food_and_vehicle_add = fields.Float(string='Food and vehicle add')
    long_year_add = fields.Float(string='Long year add')
    health_insurance = fields.Float(string='Health insurance')
    accident_insurance = fields.Float(string='Accident insurance')
    voucher = fields.Float(string='Voucher')
    abnormal_add = fields.Float(string='Abnormal add')
    trial_end_date = fields.Float(string='Trial End Date')
    insurance_type_id = fields.Many2one('insurance.type', 'Insurance Type')

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    dep_id = fields.Many2one('hr.department', string='Department')
    payslip_type = fields.Selection([('advance', 'Урьдчилгаа цалин'),
                                     ('final', 'Сүүл цалин')],
                                    string='Цалингийн төрөл', required=True, default='final')
    advance_run_id = fields.Many2one('hr.payslip.run', string='Урьдчилгаа цалингийн багц',
                                     domain="[('payslip_type', '=', 'advance'), ('state', '=', 'done'), ('id', '!=', id)]",
                                     help='Сүүл цалин бодоход энэ багцын урьдчилгааг ADV суутгалд татна.')

    @api.onchange('payslip_type')
    def _onchange_payslip_type(self):
        if self.payslip_type == 'advance':
            self.advance_run_id = False

# Цалингийн хуудсын багцын жагсаалтын багана -> цалингийн дүрмийн код(ууд)
PAYSLIP_COLUMN_CODES = {
    'wage_amount': ('BS',),
    'month_work_days': ('MWD',),
    'month_work_hours': ('MWT',),
    'worked_days': ('WDD',),
    'worked_hours': ('WDT',),
    'overtime_hours': ('OTH',),
    'overtime_amount': ('OT',),
    'computed_salary': ('CBS',),
    'vacation_amount': ('RS',),
    'performance_amount': ('KPI',),
    'allowance_total': ('ADT',),
    'gross_amount': ('CS',),
    'advance_amount': ('ADV',),
    'ndsh_employee_amount': ('SI11', 'SI15', 'SI10'),
    'ndsh_company_amount': ('NDSH',),
    'pit_amount': ('LLL',),
    'phone_deduction_amount': ('PH',),
    'receivable_deduction_amount': ('EDE', 'PAY', 'FAULT'),
    'deduction_total': ('TE',),
    # ADVP мөр зөвхөн урьдчилгаа цалингийн хуудсанд байна
    'net_amount': ('GIVE', 'ADVP'),
}


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    dep_id = fields.Many2one('hr.department', string='Department')
    # Буцаалтын хуудас багцгүй хуулагддаг тул related биш, хуулагддаг compute
    payslip_type = fields.Selection([('advance', 'Урьдчилгаа цалин'),
                                     ('final', 'Сүүл цалин')],
                                    string='Цалингийн төрөл', compute='_compute_payslip_type',
                                    store=True, readonly=False, copy=True)
    advance_must_hours = fields.Float(string='Ажиллах ёстой цаг', compute='_compute_advance_hours',
                                      store=True, readonly=False, copy=True,
                                      help='Цагийн бүртгэлээс авна. Гараар засаж болно.')
    advance_worked_hours = fields.Float(string='Ажилласан цаг (урьдчилгаа)', compute='_compute_advance_hours',
                                        store=True, readonly=False, copy=True,
                                        help='Цагийн бүртгэлээс авна. Гараар засаж болно.')
    prepayment_amount = fields.Float(string='Урьдчилгаа олгох дүн', compute='_compute_prepayment_amount',
                                     store=True, readonly=False, copy=True,
                                     help='Гэрээний цалин × урьдчилгааны % × ажилласан цаг / ажиллах ёстой цаг. '
                                          'Гараар засаж болно.')

    employee_last_name = fields.Char(string='Овог', compute='_compute_employee_info')
    employee_first_name = fields.Char(string='Нэр', compute='_compute_employee_info')
    employee_department_id = fields.Many2one('hr.department', string='Хэлтэс тасаг', compute='_compute_employee_info')
    employee_bank_account = fields.Char(string='Дансны дугаар', compute='_compute_employee_info')
    employee_register = fields.Char(string='Регистр №', compute='_compute_employee_info')

    wage_amount = fields.Float(string='Үндсэн цалин', compute='_compute_payslip_columns', store=True)
    month_work_days = fields.Float(string='Сарын ажлын хоног', compute='_compute_payslip_columns', store=True)
    month_work_hours = fields.Float(string='Сарын ажлын фонд цаг', compute='_compute_payslip_columns', store=True)
    worked_days = fields.Float(string='Ажилласан хоног', compute='_compute_payslip_columns', store=True)
    worked_hours = fields.Float(string='Ажилласан цаг', compute='_compute_payslip_columns', store=True)
    overtime_hours = fields.Float(string='Илүү цаг', compute='_compute_payslip_columns', store=True)
    overtime_amount = fields.Float(string='Илүү цагийн нэмэгдэл', compute='_compute_payslip_columns', store=True)
    computed_salary = fields.Float(string='Бодогдсон цалин', compute='_compute_payslip_columns', store=True)
    vacation_amount = fields.Float(string='Амралтын мөнгө', compute='_compute_payslip_columns', store=True)
    performance_amount = fields.Float(string='Гүйцэтгэлийн нэмэгдэл', compute='_compute_payslip_columns', store=True)
    other_allowance_amount = fields.Float(string='Бусад нэмэгдэл', compute='_compute_payslip_columns', store=True)
    allowance_total = fields.Float(string='Нэмэгдлийн дүн', compute='_compute_payslip_columns', store=True)
    gross_amount = fields.Float(string='Олговол зохих', compute='_compute_payslip_columns', store=True)
    advance_amount = fields.Float(string='Урьдчилгаа цалин', compute='_compute_payslip_columns', store=True)
    ndsh_employee_amount = fields.Float(string='НДШ-Даатгуулагчаас', compute='_compute_payslip_columns', store=True)
    ndsh_company_amount = fields.Float(string='НДШ Ажил олгогчоос', compute='_compute_payslip_columns', store=True)
    pit_amount = fields.Float(string='ХАОАТ', compute='_compute_payslip_columns', store=True)
    pit_percent = fields.Float(string='ХАОАТ %', compute='_compute_payslip_columns', store=True)
    phone_deduction_amount = fields.Float(string='Утасны суутгал', compute='_compute_payslip_columns', store=True)
    receivable_deduction_amount = fields.Float(string='Ажилчдаас авлага', compute='_compute_payslip_columns', store=True)
    deduction_total = fields.Float(string='Суутгалын дүн', compute='_compute_payslip_columns', store=True)
    net_amount = fields.Float(string='Гарт олгох', compute='_compute_payslip_columns', store=True)

    @api.depends('employee_id')
    def _compute_employee_info(self):
        for slip in self:
            emp = slip.employee_id.sudo()
            slip.employee_last_name = emp['last_name'] if 'last_name' in emp._fields else False
            slip.employee_first_name = emp.name
            slip.employee_department_id = emp.department_id
            slip.employee_bank_account = emp.bank_account_id.acc_number
            slip.employee_register = emp['register_number'] if 'register_number' in emp._fields else False

    @api.depends('line_ids.code', 'line_ids.total',
                 'worked_days_line_ids.code', 'worked_days_line_ids.number_of_days')
    def _compute_payslip_columns(self):
        for slip in self:
            totals = {}
            for line in slip.line_ids:
                totals[line.code] = totals.get(line.code, 0.0) + line.total
            vals = {
                field_name: sum(totals.get(code, 0.0) for code in codes)
                for field_name, codes in PAYSLIP_COLUMN_CODES.items()
            }
            # Хоногийн дүрэм байхгүй бол ажилласан өдрийн мөрөөс авна
            worked_days = {wd.code: wd.number_of_days for wd in slip.worked_days_line_ids}
            if not vals['month_work_days']:
                vals['month_work_days'] = worked_days.get('MUST_WORK', 0.0)
            if not vals['worked_days']:
                vals['worked_days'] = worked_days.get('WORK100', 0.0)
            # Бусад нэмэгдэл = Нэмэгдлийн дүнгээс амралтын мөнгө, гүйцэтгэлийн нэмэгдлийг хассан үлдэгдэл
            vals['other_allowance_amount'] = (vals['allowance_total'] - vals['vacation_amount']
                                              - vals['performance_amount'])
            vals['pit_percent'] = vals['pit_amount'] / vals['wage_amount'] * 100 if vals['wage_amount'] else 0.0
            # Урьдчилгааны хуудсанд BS дүрэм бодогдохгүй тул гэрээний цалинг харуулна
            if slip.payslip_type == 'advance' and not vals['wage_amount']:
                vals['wage_amount'] = slip.contract_id.wage
            slip.update(vals)

    @api.depends('payslip_run_id.payslip_type')
    def _compute_payslip_type(self):
        for slip in self:
            if slip.payslip_run_id:
                slip.payslip_type = slip.payslip_run_id.payslip_type
            elif not slip.payslip_type:
                slip.payslip_type = 'final'

    @api.depends('payslip_type', 'worked_days_line_ids.code', 'worked_days_line_ids.number_of_hours')
    def _compute_advance_hours(self):
        for slip in self:
            if slip.payslip_type != 'advance':
                slip.advance_must_hours = slip.advance_worked_hours = 0.0
            elif slip.state == 'draft':
                hours = {wd.code: wd.number_of_hours for wd in slip.worked_days_line_ids}
                slip.advance_must_hours = hours.get('MUST_WORK', 0.0)
                slip.advance_worked_hours = hours.get('WORK100', 0.0)

    @api.depends('payslip_type', 'contract_id.wage',
                 'advance_must_hours', 'advance_worked_hours')
    def _compute_prepayment_amount(self):
        for slip in self:
            if slip.payslip_type != 'advance':
                slip.prepayment_amount = 0.0
            elif slip.state == 'draft':
                # Батлагдсан хуудасны дүнг гэрээ өөрчлөгдсөн ч хөндөхгүй
                # Ажиллах ёстой цаг 0 бол цагаар хуваахгүй, бүтэн цалингаас бодно
                if slip.contract_id.contract_type_id and slip.contract_id.contract_type_id.code == 'Part-Time':
                    slip.prepayment_amount = slip.company_id.currency_id.round(
                        slip.contract_id.wage * slip.advance_must_hours * 0.4)
                else:
                    ratio = (slip.advance_worked_hours / slip.advance_must_hours
                             if slip.advance_must_hours else 1.0)
                    slip.prepayment_amount = slip.company_id.currency_id.round(
                        slip.contract_id.wage * 40 / 100.0 * ratio)


    def write(self, vals):
        res = super(HrPayslip, self).write(vals)
        # Урьдчилгааны хувь, дүнг гараар зассан бол мөрийг шууд шинэчилнэ
        if {'prepayment_amount', 'advance_must_hours', 'advance_worked_hours'} & set(vals):
            self.filtered(lambda s: s.payslip_type == 'advance' and s.state == 'draft')._compute_advance_sheet()
        return res

    def compute_sheet(self):
        advance_slips = self.filtered(lambda s: s.payslip_type == 'advance')
        final_slips = self - advance_slips
        final_slips._apply_advance_inputs()
        res = super(HrPayslip, final_slips).compute_sheet()
        advance_slips._compute_advance_sheet()
        return res

    def _compute_advance_sheet(self):
        """Урьдчилгаа цалингийн хуудас: цалингийн дүрмүүдийг бодохгүй, зөвхөн ADVP мөр үүсгэнэ."""
        for slip in self:
            rule = slip._get_advance_rule()
            contract = slip.contract_id or self.env['hr.contract'].browse(
                self.get_contract(slip.employee_id, slip.date_from, slip.date_to)[:1])
            if not contract:
                raise ValidationError(_("No running contract found for the employee: %s or no contract in the given period") % slip.employee_id.name)
            slip.line_ids.unlink()
            line_vals = {
                'salary_rule_id': rule.id,
                'contract_id': contract.id,
                'employee_id': slip.employee_id.id,
                'name': rule.name,
                'code': rule.code,
                'category_id': rule.category_id.id,
                'sequence': rule.sequence,
                'appears_on_payslip': rule.appears_on_payslip,
                'condition_select': 'none',
                'amount_select': 'fix',
                'register_id': rule.register_id.id,
                'amount': slip.prepayment_amount,
                'quantity': 1.0,
                'rate': 100.0,
            }
            slip_vals = {
                'number': slip.number or self.env['ir.sequence'].next_by_code('salary.slip'),
                'line_ids': [(0, 0, line_vals)],
            }
            # contract_id-г дахин бичвэл гараар зассан prepayment_amount дахин бодогдоно
            if not slip.contract_id:
                slip_vals['contract_id'] = contract.id
            super(HrPayslip, slip).write(slip_vals)

    def _get_advance_rule(self):
        """Хуудасны компанийн ADVP дүрэм. Компани бүр өөрийн данстай ADVP дүрэмтэй байж болно."""
        self.ensure_one()
        company = self.company_id or self.env.company
        rules = self.env['hr.salary.rule'].search([
            ('code', '=', 'ADVP'), ('company_id', 'in', [company.id, False])])
        rule = rules.filtered(lambda r: r.company_id == company)[:1] or rules[:1] \
            or self.env.ref('l10n_mn_payroll.adv_salary_rule')
        accounts = rule.sudo().account_debit | rule.sudo().account_credit
        wrong = accounts.filtered(lambda a: a.company_id not in company.parent_ids)
        if wrong:
            raise UserError(_('"%(rule)s" (ADVP) цалингийн дүрмийн данс %(accounts)s нь %(company)s компанийнх биш байна. '
                              'Цалингийн дүрэм дээр тухайн компанийн дансыг тохируулна уу.',
                              rule=rule.name, accounts=', '.join(wrong.mapped('code')), company=company.name))
        return rule

    def _apply_advance_inputs(self):
        """Багц дээр сонгосон урьдчилгааны багцаас ажилтны урьдчилгааг ADV оролтод татна."""
        for slip in self:
            advance_run = slip.payslip_run_id.advance_run_id
            if not advance_run:
                continue
            advance_slips = advance_run.slip_ids.filtered(
                lambda s: s.employee_id == slip.employee_id and s.state == 'done')
            amount = sum(s.net_amount * (-1 if s.credit_note else 1) for s in advance_slips)
            adv_input = slip.input_line_ids.filtered(lambda i: i.code == 'ADV')
            if adv_input:
                adv_input[0].amount = amount
                (adv_input - adv_input[0]).unlink()
            elif slip.contract_id:
                self.env['hr.payslip.input'].create({
                    'payslip_id': slip.id,
                    'name': _('Урьдчилгаа'),
                    'code': 'ADV',
                    'amount': amount,
                    'contract_id': slip.contract_id.id,
                })

    def refund_sheet(self):
        for payslip in self:
            if  payslip.credit_note == True:
                raise UserError(_(u'Буцаалт хийгдсэн тул дахин буцаалт хийхгүй.'))
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.compute_sheet()
            copied_payslip.action_payslip_done()
        formview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_tree', False)
        
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
        res = [line for line in res if line.get('code') != 'WORK100']
        employee_id = self.employee_id or contracts.employee_id
        if employee_id or contracts:
            start_date = date_from or self.date_from
            end_date = date_to or self.date_to
            hr_hour_record = self.env['hr.hour.record'].new({
                'start_date': datetime.combine(start_date, time(0, 1)) - timedelta(hours=8),
                'end_date': datetime.combine(end_date, time(23, 59)) - timedelta(hours=8),
                'company_id': self.employee_id.company_id.id
            })
            line_vals = hr_hour_record.hour_record(employee_id=employee_id)
            work_day = 0
            work_hour = 0
            worked_day = 0
            worked_hour = 0
            if 'due_day' in line_vals.keys() and 'work_day' in line_vals.keys():
                work_day = line_vals['due_day']
                work_hour = round(line_vals['due_time'], 2)
                worked_day = line_vals['work_day']
                worked_hour = round(line_vals['work_time'] + line_vals['free_time1'], 2)
            must_work = {
                'name': _("Must work"),
                'sequence': 1,
                'code': 'MUST_WORK',
                'number_of_days': work_day,
                'number_of_hours': work_hour,
                'contract_id': contracts.id
            }
            worked = {
                'name': _("Worked"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': worked_day,
                'number_of_hours': worked_hour,
                'contract_id': contracts.id
            }

            res.append(must_work)
            res.append(worked)
        return res

    @api.model
    def _get_payslip_lines(
        self,
        contract_ids,
        payslip_id,
        from_sequence=None,
    ):

        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(
                    localdict,
                    category.parent_id,
                    amount
                )

            localdict['categories'].dict[category.code] = (
                localdict['categories'].dict[category.code] + amount
                if category.code in localdict['categories'].dict
                else amount
            )

            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, data, env):
                self.employee_id = employee_id
                self.dict = data
                self.env = env

            def __getattr__(self, attr):
                return (
                    self.dict[attr]
                    if attr in self.dict
                    else 0.0
                )

        class InputLine(BrowsableObject):

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()

                self.env.cr.execute("""
                    SELECT sum(amount)
                    FROM hr_payslip hp
                    JOIN hr_payslip_input pi
                        ON hp.id = pi.payslip_id
                    WHERE hp.employee_id = %s
                      AND hp.state = 'done'
                      AND hp.date_from >= %s
                      AND hp.date_to <= %s
                      AND pi.code = %s
                """, (
                    self.employee_id,
                    from_date,
                    to_date,
                    code,
                ))

                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):

            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()

                self.env.cr.execute("""
                    SELECT
                        sum(number_of_days),
                        sum(number_of_hours)
                    FROM hr_payslip hp
                    JOIN hr_payslip_worked_days pi
                        ON hp.id = pi.payslip_id
                    WHERE hp.employee_id = %s
                      AND hp.state = 'done'
                      AND hp.date_from >= %s
                      AND hp.date_to <= %s
                      AND pi.code = %s
                """, (
                    self.employee_id,
                    from_date,
                    to_date,
                    code,
                ))

                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()

                self.env.cr.execute("""
                    SELECT sum(
                        CASE
                            WHEN hp.credit_note = FALSE
                            THEN pl.total
                            ELSE -pl.total
                        END
                    )
                    FROM hr_payslip hp
                    JOIN hr_payslip_line pl
                        ON hp.id = pl.slip_id
                    WHERE hp.employee_id = %s
                      AND hp.state = 'done'
                      AND hp.date_from >= %s
                      AND hp.date_to <= %s
                      AND pl.code = %s
                """, (
                    self.employee_id,
                    from_date,
                    to_date,
                    code,
                ))

                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []

        payslip = self.env['hr.payslip'].browse(payslip_id)

        # ---------------------------------------------------------
        # Worked days
        # ---------------------------------------------------------

        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line

        # ---------------------------------------------------------
        # Inputs
        # ---------------------------------------------------------

        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        # ---------------------------------------------------------
        # Browsable objects
        # ---------------------------------------------------------

        categories = BrowsableObject(
            payslip.employee_id.id,
            {},
            self.env
        )

        inputs = InputLine(
            payslip.employee_id.id,
            inputs_dict,
            self.env
        )

        worked_days = WorkedDays(
            payslip.employee_id.id,
            worked_days_dict,
            self.env
        )

        payslips = Payslips(
            payslip.employee_id.id,
            {},
            self.env
        )

        rules = BrowsableObject(
            payslip.employee_id.id,
            rules_dict,
            self.env
        )

        baselocaldict = {
            'categories': categories,
            'rules': rules,
            'payslip': payslips,
            'worked_days': worked_days,
            'inputs': inputs,
        }

        # ---------------------------------------------------------
        # Contracts
        # ---------------------------------------------------------

        contracts = self.env['hr.contract'].browse(contract_ids)

        if not contracts:
            return []

        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(
                set(
                    payslip.struct_id
                    ._get_parent_structure()
                    .ids
                )
            )
        else:
            structure_ids = contracts.get_all_structures()

        # ---------------------------------------------------------
        # Salary rules
        # ---------------------------------------------------------

        rule_ids = (
            self.env['hr.payroll.structure']
            .browse(structure_ids)
            .get_all_rules()
        )

        sorted_rule_ids = [
            rule_id
            for rule_id, sequence in sorted(
                rule_ids,
                key=lambda x: x[1]
            )
        ]

        sorted_rules = self.env['hr.salary.rule'].browse(
            sorted_rule_ids
        )

        # ---------------------------------------------------------
        # Process contracts
        # ---------------------------------------------------------

        for contract in contracts:

            employee = contract.employee_id

            localdict = dict(
                baselocaldict,
                employee=employee,
                contract=contract,
            )

            # Existing lines for this contract
            existing_lines = payslip.line_ids.filtered(
                lambda line:
                    line.contract_id.id == contract.id
            )

            # -----------------------------------------------------
            # Run rules by sequence
            # -----------------------------------------------------

            for rule in sorted_rules:

                key = f'{rule.code}-{contract.id}'

                # =================================================
                # IMPORTANT:
                #
                # If from_sequence is provided and this rule is
                # before/equal to changed line sequence:
                #
                # DO NOT calculate it again.
                #
                # Instead use existing line values to rebuild:
                #   - localdict[rule.code]
                #   - rules
                #   - categories
                #   - result_dict
                # =================================================

                if (
                    from_sequence is not None
                    and rule.sequence <= from_sequence
                ):
                    existing_line = existing_lines.filtered(
                        lambda line:
                            line.salary_rule_id.id == rule.id
                    )[:1]

                    if existing_line:

                        total = existing_line.total

                        # This is what later Python rules use:
                        #
                        # BASIC
                        # GROSS
                        # NET
                        # etc.
                        localdict[rule.code] = total

                        # rules.BASIC / rules.GROSS ...
                        rules_dict[rule.code] = rule

                        # Categories must also be reconstructed.
                        localdict = _sum_salary_rule_category(
                            localdict,
                            rule.category_id,
                            total
                        )

                        # Keep existing line in result
                        result_dict[key] = {
                            'salary_rule_id': rule.id,
                            'contract_id': contract.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip':
                                rule.appears_on_payslip,
                            'condition_select':
                                rule.condition_select,
                            'condition_python':
                                rule.condition_python,
                            'condition_range':
                                rule.condition_range,
                            'condition_range_min':
                                rule.condition_range_min,
                            'condition_range_max':
                                rule.condition_range_max,
                            'amount_select':
                                rule.amount_select,
                            'amount_fix':
                                rule.amount_fix,
                            'amount_python_compute':
                                rule.amount_python_compute,
                            'amount_percentage':
                                rule.amount_percentage,
                            'amount_percentage_base':
                                rule.amount_percentage_base,
                            'register_id':
                                rule.register_id.id,
                            'amount':
                                existing_line.amount,
                            'employee_id':
                                contract.employee_id.id,
                            'quantity':
                                existing_line.quantity,
                            'rate':
                                existing_line.rate,
                        }

                    # IMPORTANT:
                    # Do not calculate this rule again.
                    continue

                # =================================================
                # From here:
                # rule.sequence > from_sequence
                #
                # These rules WILL be recalculated.
                # =================================================

                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100

                # -------------------------------------------------
                # Condition
                # -------------------------------------------------

                if rule._satisfy_condition(
                    localdict
                ) and rule.id not in blacklist:

                    # -------------------------------------------------
                    # Calculate rule
                    # -------------------------------------------------

                    amount, qty, rate = rule._compute_rule(
                        localdict
                    )

                    previous_amount = (
                        localdict.get(rule.code, 0.0)
                    )

                    total = (
                        contract.company_id.currency_id.round(
                            amount * qty * rate / 100.0
                        )
                    )

                    # -------------------------------------------------
                    # Update localdict
                    # -------------------------------------------------

                    localdict[rule.code] = total

                    rules_dict[rule.code] = rule

                    # -------------------------------------------------
                    # Update categories
                    # -------------------------------------------------

                    localdict = _sum_salary_rule_category(
                        localdict,
                        rule.category_id,
                        total - previous_amount
                    )

                    # -------------------------------------------------
                    # Save recalculated result
                    # -------------------------------------------------

                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip':
                            rule.appears_on_payslip,
                        'condition_select':
                            rule.condition_select,
                        'condition_python':
                            rule.condition_python,
                        'condition_range':
                            rule.condition_range,
                        'condition_range_min':
                            rule.condition_range_min,
                        'condition_range_max':
                            rule.condition_range_max,
                        'amount_select':
                            rule.amount_select,
                        'amount_fix':
                            rule.amount_fix,
                        'amount_python_compute':
                            rule.amount_python_compute,
                        'amount_percentage':
                            rule.amount_percentage,
                        'amount_percentage_base':
                            rule.amount_percentage_base,
                        'register_id':
                            rule.register_id.id,
                        'amount': amount,
                        'employee_id':
                            contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }

                else:

                    # -------------------------------------------------
                    # Condition false:
                    # blacklist rule and its children
                    # -------------------------------------------------

                    blacklist += [
                        rule_id
                        for rule_id, seq
                        in rule._recursive_search_of_rules()
                    ]

            # end rule loop

        # end contract loop

        return list(result_dict.values())