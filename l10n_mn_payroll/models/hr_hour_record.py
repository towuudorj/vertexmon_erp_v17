# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo import tools, _
_logger = logging.getLogger(__name__)
from datetime import date
from datetime import timedelta
from datetime import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import json, requests
from pytz import timezone
import io
import xlsxwriter
from odoo.tools import date_utils

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class HrLeave(models.Model):
    _inherit = "hr.leave"

    def _get_duration(self, check_leave_type=True, resource_calendar=None):
        days, hours = super(HrLeave, self)._get_duration(check_leave_type, resource_calendar)
        resource_calendar = resource_calendar or self.resource_calendar_id
        if resource_calendar.work_time and (self.holiday_status_id.request_unit == 'day' or self.number_of_days_display >= 1):
            hours = days * resource_calendar.work_time
        return (days, hours)

class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"
    
    sub_type = fields.Selection([
                        ('legal_leave', 'Legal leave'),
                        ('sick', 'Sick'),
                        ('out_work', 'Out work'),
                        ('night_out_work', 'Night out work'),
                        ('payroll', 'Payroll'),
                        ('unpayroll', 'Unpayroll'),
                        ('over_time','Over time'),
                        ('public_holiday', 'Public holiday'),
                        ('international_holiday', 'International holiday'),
                    ], string='Sub type', required=True)
    

class HrHourRecord(models.Model):
    """ АЖИЛЧДЫН ЦАГИЙН БҮРТГЭЛ """
    _name = 'hr.hour.record'
    _inherit = ['mail.thread']
    _description = "Employee hour record"
    
    department = fields.Many2one('hr.department',string='Department')
    name = fields.Char(string='Working time register', default='/', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                 default=lambda self: self.env.company)
    start_date = fields.Datetime(string='Start date', required=True, 
                                default=fields.Date.context_today)
    end_date = fields.Datetime(string='End date',required=True, 
                                default=fields.Date.context_today)
    work_day = fields.Float(string="Work day")
    holiday_day = fields.Float(string='Holiday day')
    is_compute = fields.Boolean(string='Is compute')
    line_id = fields.One2many('hr.hour.record.line', 'parentd_id', string='Hour record')
    state = fields.Selection([
                        ('draft', 'Draft'),
                        ('confirmed', 'Confirmed'),
                        ('posted','Posted'),
                        ('done','Done'),
                    ], string='States', default='draft',
                    readonly=True, tracking=True)

    

    def hour_record(self):
        hr_data = self
        emp_info = self.env['hr.hour.record.line']
        emp_obj = self.env['hr.employee']
        att_obj = self.env['hr.attendance']
        contract_obj = self.env['hr.contract']
        holiday_obj = self.env['hr.leave']
        mach = 8
        self.delete_lines()
        emp_id = []
        company = hr_data.company_id
        if hr_data.department.id !=[]:
            emp_id = emp_obj.search([('company_id','=',company.id),('department_id','=',hr_data.department.id)], order='department_id')
        else:
            emp_id = emp_obj.search([('company_id','=',company.id)], order='department_id')
            
        start_date = hr_data.start_date
        end_times = hr_data.end_date + timedelta(hours=mach)
        end_time = end_times.replace(minute=59, hour=23, second=59)
        emp_attendance_ids = emp_id.mapped('timely_id')
        timely_data = self.get_timely_data(emp_attendance_ids)
        timely_worker_ids = timely_data.keys() if timely_data else []
        for line in emp_id:
            due_time=0
            due_day=0
            in_time = 0.0
            n_time = 0.00
            out_n_time = 0.0
            worked_day = 0.0
            over_time = 0.0

            payroll_time = 0.0
            unpayroll_time = 0.0
            shift_time = 0.0
            out_time = 0.0
            official_time = 0.0
            sick_time = 0.0
            shift_day = 0.0
            lost_time = 0.0
            free_time1 = 0.0
            lost_time_dict = {}
            work_day = start_date
            att_id = att_obj.search([('employee_id','=',line.id),('check_in','>=',start_date),('check_out','<=',end_time)])
            contract_id = contract_obj.search([('employee_id', '=', line.id), ('state', '=', 'open')])
            if not contract_id or not contract_id.resource_calendar_id and (not str(line.timely_id) in timely_worker_ids):
                raise UserError(u"%s энэ ажилтаны гэрээ үүсээгүй эсвэл гэрээ нь дээр цагийн хуваарь оруулаагүй байна !" % line.name)
            if att_id and not str(line.timely_id) in timely_worker_ids:
                work_weekdays = contract_id.resource_calendar_id.attendance_ids.mapped('dayofweek')
                while work_day <= end_time:
                    worked_hour = 0
                    if str(work_day.weekday()) in work_weekdays:
                        due_day += 1
                        due_time += mach
                        for att_line1 in att_id:
                            if att_line1.check_in.date() == work_day.date():
                                work_start = att_line1.check_in
                                work_end = att_line1.check_out
                                tz = company.partner_id.tz if company.partner_id.tz else 'Asia/Ulaanbaatar'
                                company_tz = timezone(tz)
                                work_start = work_start.astimezone(company_tz)
                                work_end = work_end.astimezone(company_tz)
                                lunch_hour = 1
                                lunch_start_time = work_start
                                lunch_end_time = work_start
                                if contract_id.resource_calendar_id.lunchtime_start:
                                    lunch_start_time = lunch_start_time.replace(hour=int(round(contract_id.resource_calendar_id.lunchtime_start, 0)),
                                                                          minute=int(contract_id.resource_calendar_id.lunchtime_start%1*60), second=0, microsecond=0)
                                    lunch_end_time = lunch_end_time.replace(hour=int(round(contract_id.resource_calendar_id.lunchtime_end, 0)),
                                                                        minute=int(contract_id.resource_calendar_id.lunchtime_end%1*60), second=0, microsecond=0)
                                else:
                                    lunch_start_time = lunch_start_time.replace(hour=12, minute=0, second=0, microsecond=0)
                                    lunch_end_time = lunch_end_time.replace(hour=13, minute=0, second=0, microsecond=0)

                                if lunch_start_time < work_start < lunch_end_time:
                                    delta = work_start - lunch_start_time
                                    lunch_hour = lunch_hour - delta.total_seconds() / 60 / 60
                                if lunch_start_time < work_end < lunch_end_time:
                                    delta = lunch_end_time - work_end
                                    lunch_hour = lunch_hour - delta.total_seconds() / 60 / 60
                                if work_start >= lunch_end_time or work_end <= lunch_start_time:
                                    lunch_hour = 0
                                if lunch_hour < 0:
                                    lunch_hour = 0

                                work_start = work_start + timedelta(hours=lunch_hour)
                                delta = work_end - work_start
                                worked_hour = delta.total_seconds() / 60 / 60
                                if worked_hour > 0:
                                    in_time += worked_hour
                                    worked_day += 1
                    if not worked_hour > 0:
                        must_work_hour = contract_id.resource_calendar_id.work_time if contract_id.resource_calendar_id.work_time > 0 else 8
                        lost_time += must_work_hour - worked_hour
                        lost_time_dict[work_day] = must_work_hour - worked_hour
                    work_day = work_day + timedelta(days=1)


            holiday_id1 = holiday_obj.search([('employee_id','=',line.id),('date_from','>=',start_date),('state','=','validate')])
            if holiday_id1 and not str(line.timely_id) in timely_worker_ids:
                for lines1 in holiday_id1:
                    if lines1.holiday_status_id.sub_type == 'public_holiday':
                        if lines1.date_to <= end_time:
                            shift_time = lines1.number_of_days
                        elif lines1.date_from > end_time:
                            shift_time = 0
                        else:
                            shift_time = 0
                            s_date = lines1.date_from
                            while s_date <= end_time:
                                shift_time += 1
                                s_date = s_date + timedelta(days=1)


            holiday_id = holiday_obj.search([('employee_id','=',line.id),('date_from','>=',start_date),('state','=','validate')])
            if holiday_id and not str(line.timely_id) in timely_worker_ids:
                for lines in holiday_id:
                    if lines.date_from:
                        if lines.date_to <= end_time:
                            holiday_days = lines.number_of_days
                        elif lines.date_from > end_time:
                            holiday_days = 0
                        else:
                            holiday_days = 0
                            s_date = lines.date_from
                            while s_date <= end_time:
                                holiday_days += 1
                                s_date = s_date + timedelta(days=1)

                        if lines.number_of_days_display >= 1:
                            if lines.holiday_status_id.sub_type == 'night_out_work':
                                n_time += holiday_days*mach

                            elif lines.holiday_status_id.sub_type == 'over_time':
                                over_time += holiday_days*mach

                            elif lines.holiday_status_id.sub_type == 'unpayroll':
                                unpayroll_time += holiday_days*mach

                            elif lines.holiday_status_id.sub_type == 'out_work':
                                out_n_time +=holiday_days*mach

                            elif lines.holiday_status_id.sub_type in ['payroll', 'international_holiday']:
                                free_time1 +=holiday_days*mach

                            elif lines.holiday_status_id.sub_type == 'legal_leave':
                                official_time +=holiday_days*mach

                            elif lines.holiday_status_id.sub_type == 'sick':
                                sick_time +=holiday_days*mach

                        else:
                            if lines.date_to <= end_time:
                                if lines.holiday_status_id.sub_type == 'night_out_work':
                                    n_time +=lines.number_of_hours_display

                                elif lines.holiday_status_id.sub_type == 'over_time':
                                    over_time += lines.number_of_hours_display
                                elif lines.holiday_status_id.sub_type == 'unpayroll':

                                    unpayroll_time += lines.number_of_hours_display
                                elif lines.holiday_status_id.sub_type == 'out_work':
                                    out_n_time +=lines.number_of_hours_display

                                elif lines.holiday_status_id.sub_type in ['payroll', 'international_holiday']:
                                    free_time1 +=lines.number_of_hours_display

                                elif lines.holiday_status_id.sub_type == 'legal_leave':
                                    official_time +=lines.number_of_hours_display

                                elif lines.holiday_status_id.sub_type == 'sick':
                                    sick_time +=lines.number_of_hours_display

            if str(line.timely_id) in timely_worker_ids:
                emp_hour_balance = timely_data[str(line.attendance_id)]
                due_day += emp_hour_balance['attd']['work']['day']
                due_time += emp_hour_balance['attd']['work']['time']
                worked_day += emp_hour_balance['attd']['total_worked']['day']
                in_time += emp_hour_balance['attd']['total_worked']['time']
                # sick_time += emp_hour_balance['attd']['sick_time']
                n_time += emp_hour_balance['attd']['overtime_night']['time']
                # shift_time += emp_hour_balance['attd']['vacation_day']
                lost_time += emp_hour_balance['attd']['total_unworked']['time']
                # free_time1 += emp_hour_balance['attd']['salary_leave_time']
                unpayroll_time_api = 0
                for request in emp_hour_balance['request']:
                    if request['code'] == 'app_leave_normal':
                        unpayroll_time_api += request['totalTime']
                unpayroll_time += unpayroll_time_api
                over_time += emp_hour_balance['attd']['overtime_subtraction']['time']
                official_time += emp_hour_balance['attd']['holiday_worked']['time']
            total_time = in_time + official_time + sick_time + out_n_time + n_time
            lost_time = lost_time - (shift_time*8) - out_n_time - n_time - sick_time - free_time1 - unpayroll_time - official_time

            emp_info.create({
                'work_day':worked_day,
                'employee_id': line.id,
                'parentd_id': self.id,
                'position': line.job_id.id,
                'due_day': due_day,
                'due_time': due_time,
                'shift_holiday':shift_time,
                'outer_night_time':out_n_time,
                'night_time':n_time,
                'sick_time':sick_time,
                'miss_time':lost_time,
                'free_time1':free_time1,
                'free_time2':unpayroll_time,
                'more_time':over_time,
                'more_time1':official_time,
                'work_time':in_time,
                'total_time':total_time
            })

    def get_timely_data(self, emp_attendance_ids):
        emp_hour_balance = {}
        token_url = 'https://api.timely.mn/v3/login'
        ir_config = self.env['ir.config_parameter'].sudo()
        name = ir_config.get_param('timely_user_name', default='')
        password = ir_config.get_param('timely_password', default='')
        token = False
        if name != ' ' and password != ' ':
            data = {
                "name": name,
                "password": password,
            }
            headers = {
                'Content-Type': 'application/json',
            }
            response = requests.request("POST", token_url, headers=headers, json=data)
            response_json = response.json()
            token = response_json['data']

        if token:
            url = 'https://api.timely.mn/v3/overview-attd'
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }

            have_value = True
            page = 1

            while have_value:
                data = {
                    'company_register': self.company_id.vat,
                    'dateFrom': str(self.start_date.date()),
                    'dateTo': str(self.end_date.date()),
                    'page': page,
                    'limit': 100
                }

                response = requests.post(url, headers=headers, json=data)
                response_json = response.json()['data']
                if response.status_code == 200 and response_json and response_json['data']:
                    for res in response_json['data']:
                        if int(res['workerId']) in emp_attendance_ids:
                            emp_hour_balance[res['workerId']] = {
                                'attd': res['attd'],
                                'request': res['request'],
                            }
                else:
                    break
                page += 1

                return emp_hour_balance
        return {}

    def delete_lines(self):
        for invoice in self:
            for line in invoice.line_id:
                line.unlink()
        return True
    
    def workdaysub(uid,start_date, end_date):
        '''
        Calculate the number of working days between two dates inclusive
        (start_date <= end_date).
    
        The actual working days can be set with the optional whichdays
        parameter
        (default is MON-FRI)
        '''
        (MON, TUE, WED, THU, FRI, SAT, SUN) = range(7)
        whichdays=(MON,TUE,WED,THU,FRI)
        delta_days = (end_date - start_date).days + 1
        full_weeks, extra_days = divmod(delta_days, 7)
        # num_workdays = how many days/week you work * total # of weeks
        num_workdays = (full_weeks + 1) * len(whichdays)
        # subtract out any working days that fall in the 'shortened week'
        for d in range(1, 8 - extra_days):
                    if (end_date + timedelta(d)).weekday() in whichdays:
                                    num_workdays -= 1
        return num_workdays
    
    def action_posted(self):
        return {
            self.write({'state' : 'posted',
                                          })
        }
    def action_done(self):
        return {
            self.write({'state' : 'done',
                                          })
        }
    
    def action_cancel(self):
        return {
            self.write({'state' : 'draft',
                                          })
        }
    def action_confirm(self):
         hr_obj = self.env['hr.hour.record']
         seq = self.env['ir.sequence'].get('hr.hour.record')
         self.write({
                                      'name':seq,
                                      'state' : 'confirmed',
                                  })

         return True

    def action_compute(self):
        obj = self
        line_obj = self.env['hr.hour.record.line']
        total_time = 0.0
        for line in obj.line_id:
            total_time =line.work_time+line.night_time+line.free_time1+line.outer_night_time
            line.write({
                     'total_time':total_time
                     })
            
        return True

    def action_print_xls_report(self):
        data = {
            'res_id': self.id,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': self._name,
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': u'Цагийн тайлан'}
        }


    def get_xlsx_report(self, data, response, get_file=False):
        self_obj = self.env[self._name].browse(data['res_id'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sheet.set_landscape()
        sheet.set_paper(9)  # A4
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.repeat_rows(0, 0)
        head = workbook.add_format({
            'align': 'left',
            'font_size': 12
        })
        head_title = workbook.add_format({
            'align': 'center',
            'font_size': 16,
            'text_wrap': True,
            'bold': True
        })
        txt_center = workbook.add_format({
            'align': 'center',
            'border': 1,
            'font_size': 12,
            'bold': True
        })
        data_right = workbook.add_format({
            'align': 'right',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'num_format': '#,##0.00'
        })
        data_left = workbook.add_format({
            'align': 'left',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'num_format': '#0'
        })
        data_left_bold = workbook.add_format({
            'align': 'left',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'bold': True,
        })

        data_center = workbook.add_format({
            'align': 'center',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'num_format': '#,##0.00'
        })
        data_center_bold = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'bold': True,
        })
        sheet.set_column(0, 0, 5)
        sheet.set_row(3, 40)
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 20, 14)
        sheet.merge_range(0, 0, 0, 2, u'Байгууллагын нэр: %s' % self_obj.company_id.name, head)
        sheet.merge_range(1, 0, 1, 16, u'Цагийн тайлан', head_title)
        sheet.merge_range(2, 0, 2, 2, u'Тайлант хугацаа: %s - %s' % (self_obj.start_date.date(), self_obj.end_date.date()), head)
        rowx = 3
        colly = 0
        sheet.write(rowx, colly, u'№', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажилтны нэр', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Албан тушаал', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажиллавал зохих /хоног/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажиллавал зохих /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажилласан /хоног/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажилласан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Шөнө ажилласан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Гадуур ажилласан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Өвчтэй /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ээлжийн амралт /хоног/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Тасалсан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Цалинтай чөлөө /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Цалингүй чөлөө /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Илүү цаг /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Амралтын өдөр ажилсан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Нийт тооцоолсон цаг /цаг/', data_center_bold)
        rowx += 1
        total_1 = 0
        total_2 = 0
        total_3 = 0
        total_4 = 0
        total_5 = 0
        total_6 = 0
        total_7 = 0
        total_8 = 0
        total_9 = 0
        total_10 = 0
        total_11 = 0
        total_12 = 0
        total_13 = 0
        total_14 = 0
        numbering = 1
        if self_obj.line_id:
            for line in self_obj.line_id:
                colly = 0
                sheet.write(rowx, colly, numbering, data_left)
                colly += 1
                sheet.write(rowx, colly, line.employee_id.name, data_left)
                colly += 1
                sheet.write(rowx, colly, line.position.name, data_left)
                colly += 1
                sheet.write(rowx, colly, line.due_day, data_right)
                colly += 1
                sheet.write(rowx, colly, line.due_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.work_day, data_right)
                colly += 1
                sheet.write(rowx, colly, line.work_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.night_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.outer_night_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.sick_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.shift_holiday, data_right)
                colly += 1
                sheet.write(rowx, colly, line.miss_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.free_time1, data_right)
                colly += 1
                sheet.write(rowx, colly, line.free_time2, data_right)
                colly += 1
                sheet.write(rowx, colly, line.more_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.more_time1, data_right)
                colly += 1
                sheet.write(rowx, colly, line.total_time, data_right)
                colly += 1

                total_1 += line.due_day
                total_2 += line.due_time
                total_3 += line.work_day
                total_4 += line.work_time
                total_5 += line.night_time
                total_6 += line.outer_night_time
                total_7 += line.sick_time
                total_8 += line.shift_holiday
                total_9 += line.miss_time
                total_10 += line.free_time1
                total_11 += line.free_time2
                total_12 += line.more_time
                total_13 += line.more_time1
                total_14 += line.total_time

                rowx += 1
                numbering += 1

        sheet.merge_range(rowx, 0, rowx, 2, u'Нийт', data_center_bold)
        sheet.write(rowx, 3, total_1, data_right)
        sheet.write(rowx, 4, total_2, data_right)
        sheet.write(rowx, 5, total_3, data_right)
        sheet.write(rowx, 6, total_4, data_right)
        sheet.write(rowx, 7, total_5, data_right)
        sheet.write(rowx, 8, total_6, data_right)
        sheet.write(rowx, 9, total_7, data_right)
        sheet.write(rowx, 10, total_8, data_right)
        sheet.write(rowx, 11, total_9, data_right)
        sheet.write(rowx, 12, total_10, data_right)
        sheet.write(rowx, 13, total_11, data_right)
        sheet.write(rowx, 14, total_12, data_right)
        sheet.write(rowx, 15, total_13, data_right)
        sheet.write(rowx, 16, total_14, data_right)

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return


class hr_hour_record_line(models.Model):
    '''
    Ажилтаны цагийн бүртгэлийн мөр
    '''
    _name = "hr.hour.record.line"
    _order = "position"
    _description = 'Information on a employee'
    

    employee_id = fields.Many2one('hr.employee', 'Employee name')
    position = fields.Many2one('hr.job','Position')
    due_day = fields.Integer('due day')
    due_time = fields.Integer('due time')
    work_day = fields.Integer('work day')
    work_time = fields.Float('work time')
    sick_time = fields.Float('sick time')
    outer_night_time = fields.Float('Гадуур ажилсан')
    shift_holiday = fields.Float('Shift holiday')
    miss_time = fields.Float('miss time')
    night_time = fields.Float('Night work time')
    free_time1 = fields.Float(u'Гадуур ажил')
    free_time2 = fields.Float('free time2')
    more_time = fields.Float('more time')
    more_time1 = fields.Float('Legal holiday')
    late_minut = fields.Float('late minut')
    total_time = fields.Float('Total compute time')
    fine_size = fields.Integer('Attendance  bonus')
    execution_percent = fields.Integer('execution percent')
    parentd_id = fields.Many2one('hr.hour.record')
        
    
    def onchange_change_time(self, day):
        obj = self.browse(cr, uid, ids)
        due_time = 0.0
        miss_time = 0.0
        over_time = 0.0
        diff_time = 0.0
        if day:
            due_time = day*8
            diff_time = obj.work_time-due_time
            if diff_time > 0.0:
                over_time = diff_time
            else:
                miss_time = -diff_time
            
        
        res = {'value':{
                        'due_time':due_time,
                        'miss_time':miss_time,
                        'more_time':over_time,
                            }}
        return res
    
    def onchange_work_time(self, work):
        obj = self.browse(cr, uid, ids)
        miss_time = 0.0
        over_time = 0.0
        diff_time = 0.0
        if work:
            diff_time = work-obj.due_time
            if diff_time > 0.0:
                over_time = diff_time
            else:
                miss_time = -diff_time
            
        
        res = {'value':{
                        'work_time':work,
                        'miss_time':miss_time,
                        'more_time':over_time,
                        }}
        return res
   
