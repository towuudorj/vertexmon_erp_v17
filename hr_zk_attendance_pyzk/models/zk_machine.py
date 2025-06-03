    # -*- coding: utf-8 -*-
###################################################################################
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
import pytz
import sys
import logging
import binascii
import os
import platform
import subprocess
import time

from datetime import date
from datetime import timedelta
from datetime import datetime
from odoo.tools import format_datetime

from odoo import api, fields, models
from odoo import _
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Unable to import pyzk library. Try 'pip3 install pyzk'.")
    
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    device_id = fields.Char(string='Biometric Device ID')
    register_date = fields.Date(string='Register date',default=fields.Date.context_today)
    in_image = fields.Binary(string='In image')
    out_image = fields.Binary(string='Out image')
    is_mobile = fields.Boolean(string='Is Mobile')
    

    
    @api.model
    def write(self, vals):
        if 'is_mobile' in vals:
            server_time_start = datetime.now()
            vals['check_out'] = server_time_start
        return super(HrAttendance, self).write(vals)

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                raise UserError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                    'empl_name': attendance.employee_id.name,
                    'datetime': format_datetime(self.env, attendance.check_in, dt_format=False),
                })

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                #===============================================================
                # if no_check_out_attendances:
                #     raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s") % {
                #         'empl_name': attendance.employee_id.name,
                #         'datetime': format_datetime(self.env, no_check_out_attendances.check_in, dt_format=False),
                #     })
                #===============================================================
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    raise UserError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                        'empl_name': attendance.employee_id.name,
                        'datetime': format_datetime(self.env, last_attendance_before_check_out.check_in, dt_format=False),
                    })


class ZkMachine(models.Model):
    _name = 'zk.machine'
    _description = 'Zk machine'
    
    name = fields.Char(string='Machine IP', required=True)
    port_no = fields.Integer(string='Port No', required=True, default="4370")
    address_id = fields.Many2one('res.partner', string='Working Address')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    zk_timeout = fields.Integer(string='ZK Timeout', required=True, default="120")
    zk_after_date =  fields.Datetime(string='Attend Start Date', help='If provided, Attendance module will ignore records before this date.')

    #@api.multi
    def device_connect(self, zkobj):
        try:
            conn =  zkobj.connect()
            return conn
        except:
            _logger.info("zk.exception.ZKNetworkError: can't reach device.")
            raise UserError("Connection To Device cannot be established.")
            return False

    #@api.multi
    def try_connection(self):
        for r in self:
            machine_ip = r.name
            if platform.system() == 'Linux':
                response = os.system("ping -c 1 " + machine_ip)
                if response == 0:
                    raise UserError("Biometric Device is Up/Reachable.")
                else:
                    raise UserError("Biometric Device is Down/Unreachable.") 
            else:
                prog = subprocess.run(["ping", machine_ip], stdout=subprocess.PIPE)
                if 'unreachable' in str(prog):
                    raise UserError("Biometric Device is Down/Unreachable.")
                else:
                    raise UserError("Biometric Device is Up/Reachable.")  
    
    #@api.multi
    def clear_attendance(self):
        for info in self:
            try:
                machine_ip = info.name
                zk_port = info.port_no
                timeout = info.zk_timeout
                try:
                    zk = ZK(machine_ip, port = zk_port , timeout=timeout, password=0, force_udp=False, ommit_ping=False)
                except NameError:
                    raise UserError(_("Pyzk module not Found. Please install it with 'pip3 install pyzk'."))                
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        #conn.clear_attendance()
                        self._cr.execute("""delete from zk_machine_attendance""")
                        conn.disconnect()
                        raise UserError(_('Attendance Records Deleted.'))
                    else:
                        raise UserError(_('Unable to clear Attendance log. Are you sure attendance log is not empty.'))
                else:
                    raise UserError(_('Unable to connect to Attendance Device. Please use Test Connection button to verify.'))
            except:
                raise ValidationError('Unable to clear Attendance log. Are you sure attendance device is connected & record is not empty.')

    def zkgetuser(self, zk):
        try:
            users = zk.get_users()
            print(users)
            return users
        except:
            raise UserError(_('Unable to get Users.'))

    @api.model
    def cron_download(self):
        machines = self.env['zk.machine'].search([])
        for machine in machines :
            machine.download_attendance()
        
    #@api.multi
    def download_attendance(self):
        _logger.info("++++++++++++Cron Executed++++++++++++++++++++++")
        zk_attendance = self.env['zk.machine.attendance']
        att_obj = self.env['hr.attendance']
        for info in self:
            machine_ip = info.name
            zk_port = info.port_no
            timeout = info.zk_timeout
            try:
                zk = ZK(machine_ip, port = zk_port , timeout=timeout, password=0, force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(_("Pyzk module not Found. Please install it with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            if conn:
                # conn.disable_device() #Device Cannot be used during this time.
                try:
                    user = conn.get_users()
                except:
                    user = False
                try:
                    attendance = conn.get_attendance()
                except:
                    attendance = False
                if attendance:
                    for each in attendance:
                        atten_time = each.timestamp
                        atten_time = datetime.strptime(atten_time.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
                        if info.zk_after_date == False:
                            tmp_zk_after_date = datetime.strptime('2000-01-01',"%Y-%m-%d")
                        else:
                            tmp_zk_after_date = datetime.strptime(str(info.zk_after_date),'%Y-%m-%d %H:%M:%S')
                        if atten_time != False and atten_time > tmp_zk_after_date:
                            local_tz = pytz.timezone(
                                self.env.user.partner_id.tz or 'GMT')
                            local_dt = local_tz.localize(atten_time, is_dst=None)
                            utc_dt = local_dt.astimezone(pytz.utc)
                            utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                            atten_time = datetime.strptime(
                                utc_dt, "%Y-%m-%d %H:%M:%S")
                            tmp_utc = local_dt.astimezone(pytz.utc)
                            tmp_attend = tmp_utc.strftime("%Y-%m-%d %H:%M:%S")
                            
                            #===================================================
                            # 
                            # ENDEES doosh bichsen bgaa haasan print - vvdiig bitgii ustgaarai. Test bolon aldaa shalgahad neegeed ajilluulahad togs shalgah loguud shvv
                            # 
                            #===================================================
                            
                            atten_time55 = local_dt.strftime("%Y-%m-%d %H:%M:%S")
                            #print('Anh machine-s irj bga tsag SERVER tsag = MN tsagaar --hagas bvtniig duudahgvi bga', atten_time55)
                            atten_time = (datetime.strptime(str(atten_time55), "%Y-%m-%d %H:%M:%S"))#MN tsagaar
                            #print('Sistem deer bga chigeer n vzvvlj bgaa buyu MN-eer boditoi tsag', atten_time)
                            if user:
                                for uid in user:
                                    if uid.user_id == each.user_id:
                                        get_user_id = self.env['hr.employee'].search(
                                            [('device_id', '=', str(each.user_id)),('company_id','=',self.company_id.id)])
                                        #if get_user_id and get_user_id.device_id == '27':
                                        if get_user_id:
                                            
                                            biom_date = (datetime.strptime(str(atten_time), "%Y-%m-%d %H:%M:%S")).date()
                                            biom_datetime = (datetime.strptime(str(atten_time), "%Y-%m-%d %H:%M:%S"))
                                            #print ('machine-s awsan bodit odor ---ODOR, OGNOO', biom_date, biom_datetime)
                                            
                                            biom_date_start = biom_datetime.replace(hour=0, minute=0, second=1) - timedelta(hours=8)
                                            biom_date_end = biom_datetime.replace(hour=23, minute=59, second=59) - timedelta(hours=8)
                                            #print ('Sistemees shvvh 2 ognoo buyu system deer haragdaj bgaagaas 8tsag hassanaar shvvj baij bodit utgaa awna', biom_date_start, biom_date_end)
                                            biom_date_fixed2 = ((datetime.strptime(str(atten_time), "%Y-%m-%d %H:%M:%S"))).date()
                                            #print('Bodit tsagiin zowhon odriig olow', biom_date_fixed2)
                                            attend_have = att_obj.search([('employee_id', '=', get_user_id.id),('check_in', '>=', biom_date_start),('check_in', '<=', biom_date_end)],order="check_in desc",limit=1)
                                            if get_user_id.id==277:
                                                print("ddddddddddddddddddddddd",atten_time)
                                            if attend_have:
                                                check_in = (datetime.strptime(str(attend_have.check_in), "%Y-%m-%d %H:%M:%S")) + timedelta(hours=8)#MN tsagaar
                                                #print ('Bodit tsagaar buyu MN tsagaar check_in', check_in)
                                                attend_have_only_date = (datetime.strptime(str(check_in), "%Y-%m-%d %H:%M:%S")).date()#MN tsagaar
                                                #print ('Bodit tsagaar buyu MN tsagaar check_in-ii date', attend_have_only_date)
                                                #print('atten_time - tohooromjnoos awch bui ognoo 8nemeegvi buyu bodit', atten_time)
                                                #Shvvgdej irsen 1 irtsiin orohtoi ijil bwal pass hiine
                                                if check_in == atten_time:
                                                    #print('check_in == atten_time ijil tsag baigaa tul PASSSSSS hiiw', check_in, atten_time)
                                                    pass
                                                #Shvvgdej irsen 1 irtsiin orohtoi ijil bish bwal
                                                else:
                                                    #Shvvgdej irsen 1 irtsiin orohtoi ijil bish bogood garah n hooson bwal
                                                    if attend_have.check_out == False:
                                                        #print('check_in-ii bodit date',attend_have_only_date, 'atten_time-n bodit date', biom_date_fixed2)
                                                        #2 ognoo 1 odriinh bwal
                                                        if attend_have_only_date == biom_date_fixed2:
                                                            atten_time4 = (datetime.strptime(str(atten_time), "%Y-%m-%d %H:%M:%S")) - timedelta(hours=8)
                                                            #print ('WRITE hiihdee bodit atten_time-s 8tsag hasch bichij baij sitem deer zow orno. 8 hassan ognoo', atten_time4)
                                                            #if check_in > atten_time:
                                                            #    attend_have.write({'check_in': atten_time4})
                                                            if check_in < atten_time:
                                                                attend_have.write({'check_out': atten_time4})
                                                    #Shvvgdej irsen 1 irtsiin orohtoi ijil bish bogood garah n hooson bish bwal
                                                    else:
                                                        check_out = (datetime.strptime(str(attend_have.check_out), "%Y-%m-%d %H:%M:%S")) + timedelta(hours=8)
                                                        #print ('Bodit tsagaar buyu MN tsagaar check_out', check_out)
                                                        #Tohooromjnoos irj bui ognoo n ERP-s oldson irtsiin gold bwal pass hiine
                                                        #print('CHECK_IN BODIT', check_in, 'CHECK_OUT BODIT', check_out, 'ATTEN_TIME BODIT', biom_datetime)
                                                        if check_in < biom_datetime and check_out >= biom_datetime:
                                                            #print ('PASSSSSSS')
                                                            pass
                                                        #Tohooromjnoos irj bui ognoo n ERP-s oldson irtsiin garahaas ih bwal garah ognood n bichne
                                                        elif check_out < biom_datetime:
                                                            #print ('ATTEN_TIME n CHECK_OUT-aas ih ved', check_out, '<', biom_datetime)
                                                            #2 ognoo 1 odriinh bwal
                                                            if attend_have_only_date == biom_date_fixed2:
                                                                atten_time5 = (datetime.strptime(str(atten_time), "%Y-%m-%d %H:%M:%S")) - timedelta(hours=8)
                                                                #print ('WRITE hiihdee bodit atten_time-s 8tsag hasch bichij baij sitem deer zow orno. 8 hassan ognoo', atten_time5)
                                                                attend_have.write({'check_out': atten_time5})
                                                        #Tohooromjnoos irj bui ognoo n ERP-s oldson irtsiin orohoos baga bwal oroh ognood n bichne
                                                        elif check_in > biom_datetime:
                                                            #print ('ATTEN_TIME n CHECK_OUT-aas ih ved', check_out, '<', biom_datetime)
                                                            #2 ognoo 1 odriinh bwal
                                                            if attend_have_only_date == biom_date_fixed2:
                                                                atten_time52 = (datetime.strptime(str(atten_time), "%Y-%m-%d %H:%M:%S")) - timedelta(hours=8)
                                                                #print ('WRITE hiihdee bodit atten_time-s 8tsag hasch bichij baij sitem deer zow orno. 8 hassan ognoo', atten_time5)
                                                                #attend_have.write({'check_in': atten_time52})
                                            else:
                                                atten_time6 = (datetime.strptime(str(atten_time), "%Y-%m-%d %H:%M:%S")) - timedelta(hours=8)
                                                print ('CREATE hiihdee bodit atten_time-s 8tsag hasch bichih hassan ognoo', atten_time6)
                                                created_atttt = att_obj.create({'employee_id': get_user_id.id,'check_in': atten_time6})
                                            
                                        else:
                                            pass
                                    else:
                                        pass
                    # conn.enable_device() #Enable Device Once Done.
                    conn.disconnect
                    return True
                else:
                    raise UserError(_('No attendances found in Attendance Device to Download.'))
                    # conn.enable_device() #Enable Device Once Done.
                    conn.disconnect
            else:
                raise UserError(_('Unable to connect to Attendance Device. Please use Test Connection button to verify.'))

