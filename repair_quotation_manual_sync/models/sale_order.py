from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    needs_repair_sync = fields.Boolean(
        compute="_compute_needs_repair_sync"
    )

    def _get_states_for_sync(self):
        return ["draft", "sent"]

    @api.depends(
        "repair_order_ids.move_ids.repair_create_sync",
        "repair_order_ids.move_ids.repair_update_sync",
    )
    def _compute_needs_repair_sync(self):
        for order in self:
            moves = order.repair_order_ids.mapped("move_ids")
            order.needs_repair_sync = any(
                moves.filtered(
                    lambda m: m.repair_create_sync or m.repair_update_sync
                )
            )

    def action_sync_repair_lines(self):
        for order in self:
            if order.state not in order._get_states_for_sync():
                continue

            moves = order.repair_order_ids.mapped("move_ids")

            create_moves = moves.filtered(
                lambda m: m.repair_create_sync
            )
            if create_moves:
                create_moves.with_context(
                    repair_lines_manual_sync=True
                )._create_repair_sale_order_line()

            update_moves = moves.filtered(
                lambda m: m.repair_update_sync
            )
            if update_moves:
                update_moves.with_context(
                    repair_lines_manual_sync=True
                )._update_repair_sale_order_line()

        return True