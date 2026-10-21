resource "aws_db_subnet_group" "principal" {
  name       = var.proyecto
  subnet_ids = aws_subnet.privada[*].id
}

# Configuración de free tier: single-AZ, 20 GB gp2, sin Performance Insights.
resource "aws_db_instance" "principal" {
  identifier     = var.proyecto
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp2"
  storage_encrypted = true

  db_name  = "poscosegran"
  username = "poscosegran_admin"
  password = random_password.bd_maestro.result

  db_subnet_group_name   = aws_db_subnet_group.principal.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = false

  # Demo de pocos días: sin respaldos automáticos ni snapshot final.
  backup_retention_period      = 0
  skip_final_snapshot          = true
  deletion_protection          = false
  performance_insights_enabled = false
  apply_immediately            = true
}
