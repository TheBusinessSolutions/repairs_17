from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    needs_repair_sync = fields.Boolean(
        compute="_compute_needs_repair_sync"
    )

    def _get_states_for_sync(self):
        # allow sync even after confirmation
        return ["draft", "sent", "sale"]

    @api.depends(
        "repair_order_ids.move_ids.repair_create_sync",
        "repair_order_ids.move_ids.repair_update_sync",
    )
    def _compute_needs_repair_sync(self):
        for order in self:
            moves = order.repair_order_ids.mapped("move_ids")
            order.needs_repair_sync = bool(
                moves.filtered(
                    lambda m: m.repair_create_sync or m.repair_update_sync
                )
            )

    def action_sync_repair_lines(self):
        for order in self:
            order.ensure_one()

            if order.state not in order._get_states_for_sync():
                continue

            # STRICT: only moves belonging to THIS sale order
            moves = order.repair_order_ids.mapped("move_ids").filtered(
                lambda m: m.repair_id.sale_order_id.id == order.id
            )

            create_moves = moves.filtered("repair_create_sync")
            update_moves = moves.filtered("repair_update_sync")

            if create_moves:
                create_moves.with_context(
                    repair_lines_manual_sync=True
                )._create_repair_sale_order_line()

            if update_moves:
                update_moves.with_context(
                    repair_lines_manual_sync=True
                )._update_repair_sale_order_line()

        return True