# Contraseñas alfanuméricas: se insertan en URL de conexión sin codificar.
resource "random_password" "bd_maestro" {
  length  = 32
  special = false
}

resource "random_password" "bd_app" {
  length  = 32
  special = false
}

resource "random_password" "bd_migraciones" {
  length  = 32
  special = false
}

resource "random_password" "jwt_secreto" {
  length  = 48
  special = false
}

resource "random_password" "auth_local" {
  length  = 20
  special = false
}

locals {
  bd_host   = "${aws_db_instance.principal.address}:${aws_db_instance.principal.port}"
  bd_sufijo = "/${aws_db_instance.principal.db_name}?sslmode=require"

  # Parámetros SecureString de SSM (nivel estándar, gratuito).
  secretos = {
    bd_url_admin            = "postgresql+psycopg://${aws_db_instance.principal.username}:${random_password.bd_maestro.result}@${local.bd_host}${local.bd_sufijo}"
    bd_url_migraciones      = "postgresql+psycopg://poscosegran_migraciones:${random_password.bd_migraciones.result}@${local.bd_host}${local.bd_sufijo}"
    bd_url_app              = "postgresql+psycopg://poscosegran_app:${random_password.bd_app.result}@${local.bd_host}${local.bd_sufijo}"
    bd_password_app         = random_password.bd_app.result
    bd_password_migraciones = random_password.bd_migraciones.result
    jwt_secreto             = random_password.jwt_secreto.result
    auth_local_password     = random_password.auth_local.result
  }
}

resource "aws_ssm_parameter" "secreto" {
  for_each = local.secretos

  name  = "/${var.proyecto}/${each.key}"
  type  = "SecureString"
  value = each.value
}
