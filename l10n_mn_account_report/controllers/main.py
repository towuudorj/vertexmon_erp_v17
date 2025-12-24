import io
import os
import tempfile
import subprocess
from email.utils import encode_rfc2231

from odoo import http, _
from odoo.http import request


class MyReportController(http.Controller):

    @http.route('/partner_ledger/report/pdf/<int:record_id>', type='http', auth='user')
    def download_pdf(self, record_id):
        record = request.env['account.partner.ledger.excel.report'].browse(record_id)
        report_data = record.get_report_data()
        xml_data = record.get_xlsx_report(report_data, False, get_file=True)
        tmp_dir = tempfile.mkdtemp()
        xls_path = os.path.join(tmp_dir, "report.xlsx")

        with open(xls_path, "wb") as f:
            f.write(xml_data)

        pdf_path = os.path.join(tmp_dir, "report.pdf")

        subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            xls_path,
            "--outdir", tmp_dir
        ], check=True)

        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        os.remove(xls_path)
        os.remove(pdf_path)
        os.rmdir(tmp_dir)

        return request.make_response(
            pdf_data,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_data)),
                (
                    "Content-Disposition",
                    (
                        "inline; filename*=%s.pdf"
                        % encode_rfc2231('PDF Report', "utf-8")
                    ),
                ),
            ],
        )