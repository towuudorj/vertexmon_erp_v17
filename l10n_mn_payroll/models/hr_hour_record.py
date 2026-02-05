# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo import tools, _
_logger = logging.getLogger(__name__)
from datetime import date
from datetime import timedelta
from datetime import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"



class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"
    
    sub_type = fields.Selection([
                        ('legal_leave', 'Legal leave'),
                        ('sick', 'Sick'),
                        ('out_work', 'Out work'),
                        ('night_out_work', 'Night out work'),
                        ('payroll_half', 'Payroll half'),
                        ('payroll', 'Payroll'),
                        ('unpayroll', 'Unpayroll'),
                        ('over_time','Over time'),
                        ('public_holiday', 'Public holiday'),
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
        if hr_data.department.id !=[]:
            emp_id = emp_obj.search([('company_id','=',hr_data.company_id.id),('department_id','=',hr_data.department.id)], order='department_id')
        else:
            emp_id = emp_obj.search([('company_id','=',hr_data.company_id.id)], order='department_id')
            
        start_date = datetime.strptime(str(hr_data.start_date),DATETIME_FORMAT)
        end_times = datetime.strptime(str(hr_data.end_date),DATETIME_FORMAT)+timedelta(hours=8)
        end_time = end_times.replace(minute=59, hour=23, second=59)
        days = []
        idate = datetime.strptime(str(hr_data.start_date),DATETIME_FORMAT)
        while idate <= datetime.strptime(str(hr_data.end_date),DATETIME_FORMAT):
            days.append(idate)
            idate += timedelta(days = 1)
        for line in emp_id:
            due_time=0
            due_day=0
            total_work_time = 0.0
            in_time = 0.0
            out_time = 0.0
            n_time = 0.00
            out_n_time = 0.0
            fr_n_time = 0.0
            n_first_hour = 0.0
            n_first_to = 0.0
            n_second_hour = 0.0
            n_second_to = 0.0
            n_lost_minute = 0.0
            first_hour = 0.0
            first_to = 0.0
            second_hour = 0.0
            second_to = 0.0
            lost_minute = 0.0
            work_day = 0.0
            over_time = 0.0
            first_to2 = 0.0
            first_hour2 = 0.0
            second_hour2 = 0.0
            second_to2 = 0.0
            
            att_id = att_obj.search( [('employee_id','=',line.id),('check_in','>=',start_date),('check_out','<=',end_time)])
            
            
            if att_id:
                for att_line1 in att_id:
                    contract_id  = contract_obj.search([('employee_id','=',line.id),('state','=','open')])
                    if contract_id:
                        index3 = 1
                        contract =  contract_id
                        for li in contract.resource_calendar_id.attendance_ids:
                            if int(datetime.strptime(str(att_line1.check_in), "%Y-%m-%d %H:%M:%S").weekday()+1) == int(li.name):
                                if index3 == 1:
                                    first_hour = float(li.hour_from)
                                    first_to = float(li.hour_to)
                                else:
                                    second_to = float(li.hour_to)
                                index3 +=1

                        atten_time0 = datetime.strptime(str(att_line1.check_in), '%Y-%m-%d %H:%M:%S')


                        d = datetime.strptime(str(att_line1.check_in), '%Y-%m-%d %H:%M:%S')
                        dat = d.replace(minute=0, hour=6, second=0)
                        night_time = d.replace(minute=0, hour=0,second=0)

                        datas = datetime.strptime(str(dat), '%Y-%m-%d %H:%M:%S')
                        atten_time01 = atten_time0 + timedelta(hours=mach)
                        parts1 = str(atten_time01).split(' ')
                        hour_parts1 = parts1[1].split(':')
                        hour1 = int(hour_parts1[0])

                        converted_in = datetime.strptime(str(att_line1.check_in), DATETIME_FORMAT).replace(second=0) + timedelta(hours=8)
                        parts12 = str(converted_in).split(' ')
                        hour_parts12 = parts12[1].split(':')
                        login_hour = int(hour_parts12[0])

                        converted_out = datetime.strptime(str(att_line1.check_out), DATETIME_FORMAT).replace(second=0) + timedelta(hours=8)
                        parts13 = str(converted_out).split(' ')
                        hour_parts13 = parts13[1].split(':')
                        logout_hour = int(hour_parts13[0])

                        #if float(second_to) <= float(hour1):
                        if contract.resource_calendar_id.is_factory == True:
                            in_time +=att_line1.worked_hours
                        else:
                            if int(datetime.strptime(str(converted_in), "%Y-%m-%d %H:%M:%S").weekday()+1) == 6 or int(datetime.strptime(str(converted_in), "%Y-%m-%d %H:%M:%S").weekday()+1) == 7:
                                if contract.resource_calendar_id.is_holiday_time_out == True:
                                    in_time +=att_line1.worked_hours
                                else:
                                    in_time +=att_line1.worked_hours
                            else:
                                if att_line1.worked_hours < 7.0:
                                    in_time +=att_line1.worked_hours
                                else:
                                    if contract.resource_calendar_id.is_holiday_time_out == True:
                                        in_time +=att_line1.worked_hours - 1
                                    else:
                                        in_time +=att_line1.worked_hours


                        if float(22) <=float(hour1) <=float(23):
                            if float(att_line1.worked_hours)<float(9):
                                ds = datetime.strptime(str(converted_in), '%Y-%m-%d %H:%M:%S')
                                datas = ds.replace(minute=0, hour=22, second=0)
                                datass = datetime.strptime(str(datas), '%Y-%m-%d %H:%M:%S')
                                atten_time01 = atten_time0 + timedelta(hours=mach)
                                att = atten_time01-datass
                                n_time +=((att.seconds)/60)/60.0
                                if line.id == 2600:
                                    print("aldaaaaaa",n_time, hour1,att_line1.check_in)
                            else:
                                ds = datetime.strptime(str(converted_in), '%Y-%m-%d %H:%M:%S')
                                datas = ds.replace(minute=0, hour=22, second=0)
                                datass = datetime.strptime(str(datas), '%Y-%m-%d %H:%M:%S')
                                atten_time01 = atten_time0 + timedelta(hours=mach)
                                att = atten_time01-datass
                                n_time +=((att.seconds)/60)/60.0
                                if line.id == 2600:
                                    print("aldaaaaaa 1",n_time, hour1,att_line1.check_in)

                        elif float(hour1) <=float(login_hour)<=float(23) and float(logout_hour)>=float(22):
                            if float(att_line1.worked_hours)<float(9):
                                ds = datetime.strptime(str(converted_out), '%Y-%m-%d %H:%M:%S')
                                datas = ds.replace(minute=0, hour=22, second=0)
                                datass = datetime.strptime(str(datas), '%Y-%m-%d %H:%M:%S')
                                atten_time01 = atten_time0 + timedelta(hours=mach)
                                att = ds-datass
                                n_time +=((att.seconds)/60)/60.0
                                if line.id == 2600:
                                    print("aldaaaaaa 0",n_time, atten_time01,ds)
                            else:
                                ds = datetime.strptime(str(converted_out), '%Y-%m-%d %H:%M:%S')
                                datas = ds.replace(minute=0, hour=22, second=0)
                                datass = datetime.strptime(str(datas), '%Y-%m-%d %H:%M:%S')
                                atten_time01 = atten_time0 + timedelta(hours=mach)
                                att = ds-datass
                                n_time +=((att.seconds)/60)/60.0
                                if line.id == 2600:
                                    print("aldaaaaaa 11",n_time, hour1,att_line1.check_in)





                        elif float(0) <=float(logout_hour) <=float(13):
                            if float(3)<float(att_line1.worked_hours)<float(9) and str(converted_out)[:10]!=str(converted_in)[:10]:
                                ds = datetime.strptime(str(converted_out), '%Y-%m-%d %H:%M:%S')
                                datas = ds.replace(minute=0, hour=22, second=0)
                                datass = datetime.strptime(str(datas), '%Y-%m-%d %H:%M:%S')
                                atten_time01 = atten_time0 + timedelta(hours=mach)
                                att = ds-datass
                                n_time +=((att.seconds)/60)/60.0
                                if line.id == 2600:
                                    print("aldaaaaaa 2",n_time, hour1,converted_out)

                            elif float(att_line1.worked_hours)>float(9) and str(converted_out)[:10]!=str(converted_in)[:10]:
                                dst = datetime.strptime(str(converted_out), '%Y-%m-%d %H:%M:%S')
                                datss = dst.replace(minute=0, hour=22, second=0)
                                datsss = datetime.strptime(str(datss), '%Y-%m-%d %H:%M:%S')
                                atten_time02 = atten_time0 + timedelta(hours=mach)
                                attt = dst - datsss
                                new_time =((attt.seconds)/60)/60.0
                                if new_time < 8:
                                    n_time +=((attt.seconds)/60)/60.0
                                else:
                                    n_time +=8
                                if line.id == 2600:
                                    print("aldaaaaaa 3",n_time, atten_time02,dst,(attt.seconds/3600.0))
                        work_day +=1
                        
                contract_id  = contract_obj.search([('employee_id','=',line.id)])
                if contract_id:
                    contract =  contract_id
                    index = 1
                    index2 = 1
                    for att_line in att_id:
                        atten_time1 = datetime.strptime(str(att_line.check_in), '%Y-%m-%d %H:%M:%S')
                        atten_time = atten_time1 + timedelta(hours=mach)
                        parts = str(atten_time).split(' ')
                        hour_parts = parts[1].split(':')
                        minute = int(hour_parts[1])
                        hour = int(hour_parts[0])
                        for lined in contract.resource_calendar_id.attendance_ids:
                            if att_line.check_in.weekday() + 1 == int(lined.name):
                                if index == 1:
                                    first_hour = float(lined.hour_from)
                                    first_to = float(lined.hour_to)
                                else:
                                    second_hour = float(lined.hour_from)
                                    second_to = float(lined.hour_to)
                                index +=1
                        if float(first_hour) <= float(hour) <= float(first_to):
                            lost_minute += float(minute)
                       # elif float(first_hour)>= hour:
                       #     over_time += float(minute)
                        if float(second_to) < float(hour):
                            n_time
                    #else:
                        atten_time2 = datetime.strptime(str(att_line.check_out), '%Y-%m-%d %H:%M:%S')
                        atten_time2 = atten_time2 + timedelta(hours=9)
                        parts2 = str(atten_time2).split(' ')
                        hour_parts2 = parts2[1].split(':')
                        minute2 = int(hour_parts2[1])
                        hour2 = int(hour_parts2[0])
                        for lined2 in contract.resource_calendar_id.attendance_ids:
                            if int(datetime.strptime(str(att_line.check_out), "%Y-%m-%d %H:%M:%S").weekday()+1) == int(lined2.name):
                                if index2 == 1:
                                    first_hour2 = float(lined2.hour_from)
                                    first_to2 = float(lined2.hour_to)
                                else:
                                    second_hour2 = float(lined2.hour_from)
                                    second_to2 = float(lined2.hour_to)
                                index2 +=1
                                #if float(first_hour2) <= float(hour2) <= float(first_to2):
                                #    over_time += float(minute2)

                    else:

                        n_index = 1
                        for att_line in att_id:
                           # if att_line.action == 'sign_in':
                                atten_time1 = datetime.strptime(str(att_line.check_in), '%Y-%m-%d %H:%M:%S')
                                atten_time = atten_time1 + timedelta(hours=9)
                                parts = str(atten_time).split(' ')
                                hour_parts = parts[1].split(':')
                                minute = int(hour_parts[1])
                                hour = int(hour_parts[0])
                                for linee in contract.resource_calendar_id.attendance_ids:                                     
                                    if int(datetime.strptime(att_line.check_in, "%Y-%m-%d %H:%M:%S").weekday()+1) == int(linee.name):
                                        if n_index == 1:
                                            n_first_hour = float(linee.hour_from)
                                            n_first_to = float(linee.hour_to)
                                        else:
                                            n_second_hour = float(linee.hour_from)
                                            n_second_to = float(linee.hour_to)
                                        n_index +=1
                                if n_first_hour <= float(hour) <= n_first_to:
                                    n_lost_minute += float(minute)
                        
            payroll_time = 0.0
            unpayroll_time = 0.0
            shift_time = 0.0
            out_time = 0.0
            official_time = 0.0
            sick_time = 0.0
            shift_day = 0.0
            lost_time = 0.0
            fr_n_time = 0.0
            free_time1 = 0.0
            
            
            holiday_id1 = holiday_obj.search([('employee_id','=',line.id),('date_from','>=',start_date),('state','=','validate')])
            if holiday_id1:
                for lines1 in holiday_id1:
                    if lines1.holiday_status_id.new_type == 'shift_holiday':
                        shift_time = lines1.number_of_days_temp
                    
            
            holiday_id = holiday_obj.search([('employee_id','=',line.id),('date_from','>=',start_date),('date_to','<=',end_time),('state','=','validate')])
            if holiday_id:
                
                for lines in holiday_id:
                    
                    if lines.date_from !=False:
                        from_date = datetime.strptime(str(lines.date_from), '%Y-%m-%d %H:%M:%S')
                        ch_from_date = from_date + timedelta(hours=mach)
                        to_date = datetime.strptime(str(lines.date_to), '%Y-%m-%d %H:%M:%S')
                        ch_to_date = to_date + timedelta(hours=mach)
                        diff_day = ch_to_date-ch_from_date
                        diff_time = ch_to_date-ch_from_date
                        parts = str(diff_time).split(',')
                        
                        from_parts = str(ch_from_date).split(' ')
                        if len(from_parts)==1:
                            from_hours = from_parts[0].split(':')
                        else:
                            from_hours = from_parts[1].split(':')
                        end_parts = str(ch_to_date).split(' ')
                        if len(end_parts)==1:
                            end_hours = end_parts[0].split(':')
                        else:
                            end_hours = end_parts[1].split(':')
                        
                        if len(parts) == 1:
                            hours = parts[0].split(':')
                        else:
                            hours = parts[1].split(':')
                        if line.id == 2579:
                            print("aaaaaaaaa",diff_day.days,lines.holiday_status_id.new_type)
                        if int(diff_day.days) >= 1 and int(hours[0]) >= 8:
                            if lines.holiday_status_id.new_type == 'night_out_work':

                                if float(22) <=float(from_hours[0]) <=float(23):
                                    ds = datetime.strptime(str(lines.date_from), '%Y-%m-%d %H:%M:%S')
                                    datas = ds.replace(minute=0, hour=22, second=0)
                                    datass = datetime.strptime(str(datas), '%Y-%m-%d %H:%M:%S')
                                    atten_time01 = ch_to_date + timedelta(hours=mach)
                                    att = atten_time01-datass
                                    out_n_time +=((att.seconds)/60)/60.0
                                elif float(0) <=float(from_hours[0]) <=float(9):
                                    ds = datetime.strptime(str(lines.date_from), '%Y-%m-%d %H:%M:%S')
                                    datas = ds.replace(minute=0, hour=22, second=0)
                                    datass = datetime.strptime(str(datas), '%Y-%m-%d %H:%M:%S')
                                    atten_time01 = ch_to_date + timedelta(hours=mach)
                                    att = atten_time01-datass
                                    out_n_time +=((att.seconds)/60)/60.0
                                elif float(22) <=float(end_hours[0]) <=float(23):
                                    ds2 = datetime.strptime(str(ch_to_date), '%Y-%m-%d %H:%M:%S')
                                    datas2 = ds2.replace(minute=0, hour=22, second=0)
                                    datass2 = datetime.strptime(str(datas2), '%Y-%m-%d %H:%M:%S')
                                    atten_time0114 = to_date.replace(minute=0, hour=0, second=0)
                                    attds2 = atten_time0114-datass2
                                    out_n_time +=((attds2.seconds)/60.0)/60.0
                                else:
                                    payroll_time += diff_day.days*8
                                    
                            elif lines.holiday_status_id.new_type == 'over_time':
                                over_time += lines.number_of_hours_display
                                    
                            elif lines.holiday_status_id.new_type == 'unpayroll_holiday':
                                
                                unpayroll_time += lines.number_of_hours_display
                            elif lines.holiday_status_id.new_type == 'out_work':
                                free_time1 +=lines.number_of_hours_display
                            elif lines.holiday_status_id.new_type == 'payroll':
                                free_time1 +=lines.number_of_hours_display
                                
                            elif lines.holiday_status_id.new_type == 'official_work':
                                official_time +=lines.number_of_hours_display
                            elif lines.holiday_status_id.new_type == 'sick_holiday':
                                sick_time +=lines.number_of_hours_display
                                
                                
                        else:
                            if lines.holiday_status_id.new_type == 'night_out_work':
                                if line.id == 2579:
                                    print("aaaaaaaaa",diff_day.days)
                                
                                out_n_time +=lines.number_of_hours_display
 
                                    
                                if float(10) <=float(end_hours[0]) <=float(18):
                                    ds1 = datetime.strptime(str(from_date), '%Y-%m-%d %H:%M:%S')
                                    datas1 = ds1 + timedelta(hours=mach)
                                    datass1 = datetime.strptime(str(datas1), '%Y-%m-%d %H:%M:%S')
                                    atten_time0113 = to_date + timedelta(hours=mach)
                                    attds1 = atten_time0113 - datass1
                                    payroll_time +=((attds1.seconds)/3600.0)
                                else:
                                    if float(22) <=float(end_hours[0]) <=float(23):
                                        ds3 = datetime.strptime(str(from_date), '%Y-%m-%d %H:%M:%S')
                                        datas3 = ds3 + timedelta(hours=mach)
                                        datass3 = datetime.strptime(str(datas3), '%Y-%m-%d %H:%M:%S')
                                        atten_time0115 = to_date + timedelta(hours=mach)
                                        datass4 = datetime.strptime(str(atten_time0115), '%Y-%m-%d %H:%M:%S')
                                        attds3 = datass4-datass3
                                        
                                        payroll_time +=((attds3.seconds)/3600)
                                        
                                        
                                    elif float(0) <=float(end_hours[0]) <=float(6):
                                        ds2 = datetime.strptime(str(from_date), '%Y-%m-%d %H:%M:%S')
                                        datas2 = ds2 + timedelta(hours=mach)
                                        datass2 = datetime.strptime(str(datas2), '%Y-%m-%d %H:%M:%S')
                                        atten_time0114 = to_date + timedelta(hours=mach)
                                        attds2 = atten_time0114-datass2
                                        payroll_time +=((attds2.seconds)/60.0)/60.0
                                        
                                        
                            elif lines.holiday_status_id.new_type == 'over_time':
                                over_time += lines.number_of_hours_display
                            elif lines.holiday_status_id.new_type == 'unpayroll_holiday':
                                
                                unpayroll_time += lines.number_of_hours_display
                            elif lines.holiday_status_id.new_type == 'out_work':
                                free_time1 +=lines.number_of_hours_display
                            
                            elif lines.holiday_status_id.new_type == 'payroll':
                                free_time1 +=lines.number_of_hours_display
                            elif lines.holiday_status_id.new_type == 'official_work':
                                official_time +=lines.number_of_hours_display
                            elif lines.holiday_status_id.new_type == 'sick_holiday':
                                sick_time +=lines.number_of_hours_display
                        
                    

                
                
            
            
            self._cr.execute("select resource_calendar_id from hr_contract where employee_id=%s order by id desc limit 1"%(line.id))
            timetable = self._cr.fetchone()
            if timetable == None and not timetable:
               raise UserError((u"%s энэ ажилтаны гэрээ үүсээгүй эсвэл гэрээ нь дээр цагийн хуваарь оруулаагүй байна !")%(line.name))
            for day in days:
                date1 = day.strftime('%Y-%m-%d')
                self._cr.execute('''
                    select hour_from, hour_to from resource_calendar_attendance where calendar_id=%s and dayofweek='%s' order by hour_from
                '''%(timetable[0], date.weekday(datetime.strptime(date1, DATE_FORMAT))))
                fetched=self._cr.dictfetchall()
                if fetched:
                    due_day += 1
                    for worktime in fetched:
                        if line.resource_calendar_id.is_holiday_time_out==True:
                            if line.resource_calendar_id.work_time >0.0:
                                due_time += line.resource_calendar_id.work_time 
                            else:
                                due_time += worktime['hour_to'] - worktime['hour_from']
                            
                                due_time -=1
                        else:
                            if line.resource_calendar_id.work_time >0.0:
                                due_time += line.resource_calendar_id.work_time 
                            else:
                                due_time += worktime['hour_to'] - worktime['hour_from']
                        
                        
            if hr_data.holiday_day > 0.0:
                total_t = due_time/due_day
                due_day = due_day-hr_data.holiday_day
                due_time = due_day*total_t 
                
            
            total_time = in_time+payroll_time+official_time+sick_time+out_n_time

            
          
            emp_info.create({
                'work_day':work_day,
                'employee_id': line.id,
                'parentd_id': self.id,
                'position': line.job_id.id,
                'due_day': due_day,
                'due_time': due_time,
                'shift_holiday':shift_time,
                'outer_night_time':out_n_time,
                'night_time':n_time+fr_n_time,
                'sick_time':sick_time,
                'miss_time':lost_time,
                'free_time1':free_time1,
                'free_time2':unpayroll_time,
                'more_time':over_time,
                'more_time1':official_time,
                'work_time':in_time-n_time,
                'total_time':total_time
            })

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
    outer_night_time = fields.Float('Гадуур ажлын шөнийн цаг')
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
   
   


    
    