# Cadena de confianza: API Gateway (VPC Link) -> API :8000 -> RDS :5432.
resource "aws_security_group" "vpclink" {
  name        = "${var.proyecto}-vpclink"
  description = "VPC Link de API Gateway hacia la API"
  vpc_id      = aws_vpc.principal.id
}

resource "aws_security_group" "api" {
  name        = "${var.proyecto}-api"
  description = "Tareas Fargate de la API"
  vpc_id      = aws_vpc.principal.id
}

resource "aws_security_group" "rds" {
  name        = "${var.proyecto}-rds"
  description = "PostgreSQL accesible solo desde la API"
  vpc_id      = aws_vpc.principal.id
}

resource "aws_vpc_security_group_egress_rule" "vpclink_a_api" {
  security_group_id            = aws_security_group.vpclink.id
  referenced_security_group_id = aws_security_group.api.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

resource "aws_vpc_security_group_ingress_rule" "api_desde_vpclink" {
  security_group_id            = aws_security_group.api.id
  referenced_security_group_id = aws_security_group.vpclink.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

# Salida libre: ECR, SSM, CloudWatch Logs y RDS.
resource "aws_vpc_security_group_egress_rule" "api_salida" {
  security_group_id = aws_security_group.api.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_ingress_rule" "rds_desde_api" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.api.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}
