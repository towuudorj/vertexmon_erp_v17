/* @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

const STICKY_SELECTOR = [
    ".o_sticky_first_col", ".o_sticky_first_2_cols", ".o_sticky_first_3_cols", ".o_sticky_first_4_cols",
    ".o_sticky_col_1", ".o_sticky_col_2", ".o_sticky_col_3", ".o_sticky_col_4",
    ".o_x2many_sticky_col_1", ".o_x2many_sticky_col_2", ".o_x2many_sticky_col_3", ".o_x2many_sticky_col_4"
].join(", ");

/**
 * vertexmon_tools: Dynamic width calculation for sticky columns in List / x2many views.
 * Automatically measures the exact pixel width of the first N columns and sets
 * CSS variables (--o-sticky-col-X-width) on the table element for sub-pixel precision.
 */
patch(ListRenderer.prototype, {
    freezeColumnWidths() {
        super.freezeColumnWidths();
        this.updateStickyColumnOffsets();
    },

    setDefaultColumnWidths() {
        super.setDefaultColumnWidths();
        this.updateStickyColumnOffsets();
    },

    updateStickyColumnOffsets() {
        const table = this.tableRef?.el;
        if (!table) {
            return;
        }

        const isSticky = table.matches(STICKY_SELECTOR) || !!table.closest(STICKY_SELECTOR);
        if (!isSticky) {
            return;
        }

        const ths = table.querySelectorAll(":scope > thead > tr > th");
        if (ths[0]) {
            table.style.setProperty("--o-sticky-col-1-width", `${ths[0].offsetWidth}px`);
        }
        if (ths[1]) {
            table.style.setProperty("--o-sticky-col-2-width", `${ths[1].offsetWidth}px`);
        }
        if (ths[2]) {
            table.style.setProperty("--o-sticky-col-3-width", `${ths[2].offsetWidth}px`);
        }
        if (ths[3]) {
            table.style.setProperty("--o-sticky-col-4-width", `${ths[3].offsetWidth}px`);
        }
    },
});
