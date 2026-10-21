# Alerta por correo si el gasto real supera el 80 % o el previsto el 100 %.
# AWS envía primero un correo de confirmación de la suscripción.
resource "aws_budgets_budget" "mensual" {
  name         = "${var.proyecto}-mensual"
  budget_type  = "COST"
  limit_amount = tostring(var.presupuesto_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alerta_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alerta_email]
  }
}
