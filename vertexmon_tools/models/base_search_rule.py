# -*- coding: utf-8 -*-
import logging
from odoo import api, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    def check_access_rule(self, operation):
        """
        Verify that the given operation is allowed for the current user according to ir.rules.
        Standard Odoo in-memory Python filtering (_filter_access_rules_python) may fail when
        evaluating relational domains involving archived records or un-stored computed fields
        (e.g., user_id.employee_id where the employee is archived).
        When an AccessError is raised, we fall back to SQL-level access rule verification
        (_filter_access_rules) to check if the records are genuinely allowed by database rules
        before concluding that access is forbidden.
        """
        try:
            return super().check_access_rule(operation)
        except AccessError:
            if self.env.su:
                raise
            # If in-memory Python check failed, verify with SQL _filter_access_rules
            invalid = self - self._filter_access_rules(operation)
            if not invalid:
                # All records actually pass SQL-level access rules!
                return
            # Records are truly forbidden by SQL rules as well
            raise


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

