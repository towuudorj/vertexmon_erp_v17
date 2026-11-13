# -*- coding: utf-8 -*-
from odoo import api, models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def create_notification(self, email_to, subject, intro, details, url, link_label, auto_delete=False):
        """Build and create a mail.mail with a consistent notification layout.

        :param details: list of (label, value) tuples shown as a key/value table.
        """
        rows = ''.join(
            f'<tr>'
            f'<td style="padding:2px 12px 2px 0;color:#666;white-space:nowrap;">{label}</td>'
            f'<td style="padding:2px 0;font-weight:600;color:#333;">{value}</td>'
            f'</tr>'
            for label, value in details
        )
        table_html = f'<table style="border-collapse:collapse;margin:0 0 12px 0;">{rows}</table>' if details else ''
        body_html = (
            '<div style="font-family:Arial,sans-serif;font-size:13px;color:#333;">'
            f'<p style="margin:0 0 10px 0;">{intro}</p>'
            f'{table_html}'
            f'<p style="margin:0;"><a href="{url}" '
            'style="color:#714B67;font-size:16px;font-weight:600;text-decoration:none;">'
            f'{link_label} &rarr;</a></p>'
            '</div>'
        )
        # Шууд илгээхгүй: дараалалд (outgoing) үлдээж "Mail: Email Queue Manager" cron илгээнэ.
        # SMTP (Office365) хариу өгөхгүй үед товч (батлах, хүлээн авах г.м.) 60 сек+ гацахаас сэргийлнэ,
        # мөн гүйлгээ алдаатай буцвал имэйл явахгүй.
        mail = self.create({
            'email_to': email_to,
            'subject': subject,
            'body_html': body_html,
            'auto_delete': auto_delete,
        })
        return mail
