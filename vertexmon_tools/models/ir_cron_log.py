# -*- coding: utf-8 -*-
import logging
import threading
import time
import traceback
from datetime import datetime, timedelta

from odoo import api, fields, models, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Ажиллаж буй cron-ий алдааг _handle_callback_exception-аас _callback руу дамжуулна
_cron_error = threading.local()

RETENTION_PARAM = 'vertexmon_tools.cron_log_retention_days'
DEFAULT_RETENTION_DAYS = 90


class IrCronLog(models.Model):
    _name = 'ir.cron.log'
    _description = 'Scheduled Action Log'
    _order = 'start_date desc, id desc'
    _rec_name = 'cron_id'

    cron_id = fields.Many2one('ir.cron', string="Scheduled Action", required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string="Run As")
    triggered_by_id = fields.Many2one('res.users', string="Triggered By")
    trigger_type = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('manual', 'Manual'),
    ], string="Trigger", required=True, default='scheduled')
    start_date = fields.Datetime(string="Start", required=True, index=True)
    end_date = fields.Datetime(string="End")
    duration = fields.Float(string="Duration (sec)", digits=(16, 3))
    state = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string="Status", required=True, index=True)
    error_message = fields.Text(string="Error")

    @api.model
    def _write_log(self, vals):
        """Тусдаа cursor ашиглан бичнэ: cron алдаа гарвал үндсэн transaction rollback
        хийгддэг тул лог устахгүй, амжилттай үед ч cron-ий transaction-д нөлөөлөхгүй."""
        try:
            with self.pool.cursor() as cr:
                api.Environment(cr, SUPERUSER_ID, {})[self._name].create(vals)
        except Exception:
            _logger.exception("Could not write scheduled action log for cron #%s", vals.get('cron_id'))

    @api.model
    def _log_run(self, cron_id, trigger_type, start_time, error=None, user_id=None, triggered_by_id=None):
        end_time = time.time()
        self._write_log({
            'cron_id': cron_id,
            'trigger_type': trigger_type,
            'user_id': user_id,
            'triggered_by_id': triggered_by_id,
            'start_date': fields.Datetime.to_string(datetime.utcfromtimestamp(start_time)),
            'end_date': fields.Datetime.to_string(datetime.utcfromtimestamp(end_time)),
            'duration': end_time - start_time,
            'state': 'failed' if error else 'success',
            'error_message': error or False,
        })

    @api.autovacuum
    def _gc_cron_logs(self):
        days = int(self.env['ir.config_parameter'].sudo().get_param(RETENTION_PARAM, DEFAULT_RETENTION_DAYS) or 0)
        if days > 0:
            self.search([('start_date', '<', fields.Datetime.now() - timedelta(days=days))]).unlink()


class IrCron(models.Model):
    _inherit = 'ir.cron'

    log_ids = fields.One2many('ir.cron.log', 'cron_id', string="Logs")
    log_count = fields.Integer(compute='_compute_log_info', string="Log Count")
    last_log_state = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], compute='_compute_log_info', string="Last Run Status")

    def _compute_log_info(self):
        Log = self.env['ir.cron.log'].sudo()
        counts = dict(Log._read_group([('cron_id', 'in', self.ids)], ['cron_id'], ['__count']))
        for cron in self:
            cron.log_count = counts.get(cron, 0)
            last = Log.search([('cron_id', '=', cron.id)], limit=1) if cron.id else Log
            cron.last_log_state = last.state

    def action_view_logs(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('vertexmon_tools.ir_cron_log_action')
        action['domain'] = [('cron_id', '=', self.id)]
        action['context'] = {'default_cron_id': self.id}
        return action

    @api.model
    def _callback(self, cron_name, server_action_id, job_id):
        _cron_error.message = None
        start_time = time.time()
        try:
            return super()._callback(cron_name, server_action_id, job_id)
        finally:
            error = getattr(_cron_error, 'message', None)
            _cron_error.message = None
            self.env['ir.cron.log']._log_run(job_id, 'scheduled', start_time, error=error, user_id=self.env.uid)

    @api.model
    def _handle_callback_exception(self, cron_name, server_action_id, job_id, job_exception):
        _cron_error.message = traceback.format_exc()
        return super()._handle_callback_exception(cron_name, server_action_id, job_id, job_exception)

    def method_direct_trigger(self):
        for cron in self:
            # Cron өөр процесст ажиллаж байвал lock авч чадахгүй: энэ нь ажилласан run биш тул логлохгүй
            cron._try_lock()
            start_time = time.time()
            try:
                super(IrCron, cron).method_direct_trigger()
            except Exception:
                cron.env['ir.cron.log']._log_run(cron.id, 'manual', start_time, error=traceback.format_exc(),
                                                 user_id=cron.user_id.id, triggered_by_id=self.env.uid)
                raise
            cron.env['ir.cron.log']._log_run(cron.id, 'manual', start_time,
                                             user_id=cron.user_id.id, triggered_by_id=self.env.uid)
        return True
