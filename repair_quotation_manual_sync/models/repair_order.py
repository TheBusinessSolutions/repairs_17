from odoo import models


class RepairOrder(models.Model):
    _inherit = "repair.order"

    def action_create_sale_order(self):
        return super(
            RepairOrder,
            self.with_context(repair_lines_manual_sync=True),
        ).action_create_sale_order()