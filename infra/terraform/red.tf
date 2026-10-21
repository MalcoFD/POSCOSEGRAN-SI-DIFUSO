# VPC mínima sin NAT Gateway: Fargate vive en subredes públicas (con IP pública
# solo para descargar la imagen y leer SSM) y RDS en subredes privadas.
locals {
  zonas = slice(data.aws_availability_zones.disponibles.names, 0, 2)
}

resource "aws_vpc" "principal" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = var.proyecto }
}

resource "aws_internet_gateway" "principal" {
  vpc_id = aws_vpc.principal.id

  tags = { Name = var.proyecto }
}

resource "aws_subnet" "publica" {
  count = 2

  vpc_id            = aws_vpc.principal.id
  cidr_block        = cidrsubnet(aws_vpc.principal.cidr_block, 8, count.index)
  availability_zone = local.zonas[count.index]

  tags = { Name = "${var.proyecto}-publica-${count.index}" }
}

resource "aws_subnet" "privada" {
  count = 2

  vpc_id            = aws_vpc.principal.id
  cidr_block        = cidrsubnet(aws_vpc.principal.cidr_block, 8, count.index + 10)
  availability_zone = local.zonas[count.index]

  tags = { Name = "${var.proyecto}-privada-${count.index}" }
}

resource "aws_route_table" "publica" {
  vpc_id = aws_vpc.principal.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.principal.id
  }

  tags = { Name = "${var.proyecto}-publica" }
}

resource "aws_route_table_association" "publica" {
  count = 2

  subnet_id      = aws_subnet.publica[count.index].id
  route_table_id = aws_route_table.publica.id
}
