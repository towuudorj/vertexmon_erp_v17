# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        """
        Safely filter out specification fields that require groups the current user does not have,
        preventing field-level AccessError crashes during list/tree view search.
        Standard Odoo ir.rule enforcement and AccessError responses for record-level security
        are strictly preserved without any sudo() bypassing.
        """
        domain = domain or []

        # Filter out specification fields requiring groups the current user does not belong to
        safe_specification = {}
        for fname, fspec in specification.items():
            field = self._fields.get(fname)
            if field and field.groups:
                if not any(self.env.user.has_group(g.strip()) for g in field.groups.split(',')):
                    continue
            safe_specification[fname] = fspec

        # Execute standard search_fetch with safe fields
        records = self.search_fetch(domain, safe_specification.keys(), offset=offset, limit=limit, order=order)

        # Execute standard web_read
        values_records = records.web_read(safe_specification)

        # Format web search read results using standard Odoo method
        return self._format_web_search_read_results(domain, values_records, offset, limit, count_limit)

