# API Gateway HTTP API: entrega HTTPS sin dominio propio (Amplify sirve HTTPS y
# el navegador bloquearía una API HTTP) y reemplaza al ALB mediante VPC Link.
# El CORS lo resuelve FastAPI con POSCOSEGRAN_CORS_ORIGENES.
resource "aws_apigatewayv2_api" "api" {
  name          = "${var.proyecto}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_vpc_link" "api" {
  name               = "${var.proyecto}-api"
  subnet_ids         = aws_subnet.publica[*].id
  security_group_ids = [aws_security_group.vpclink.id]
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "ANY"
  integration_uri        = aws_service_discovery_service.api.arn
  connection_type        = "VPC_LINK"
  connection_id          = aws_apigatewayv2_vpc_link.api.id
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "todo" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_stage" "predeterminado" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_rate_limit  = 20
    throttling_burst_limit = 50
  }
}
