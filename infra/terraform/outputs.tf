output "frontend_url" {
  description = "Aplicación publicada por Amplify."
  value       = local.origen_web
}

output "api_url" {
  description = "Endpoint HTTPS de la API (salud en /salud/bd, documentación en /documentacion)."
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "ecr_repo_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecs_cluster" {
  value = aws_ecs_cluster.principal.name
}

output "ecs_servicio" {
  value = aws_ecs_service.api.name
}

output "amplify_app_id" {
  value = aws_amplify_app.web.id
}

output "amplify_rama" {
  value = aws_amplify_branch.principal.branch_name
}

output "region" {
  value = data.aws_region.actual.name
}

output "comando_password_login" {
  description = "Contraseña compartida de los usuarios de demo (productor, tecnico, administrador, ingeniero)."
  value       = "aws ssm get-parameter --region ${data.aws_region.actual.name} --name ${aws_ssm_parameter.secreto["auth_local_password"].name} --with-decryption --query Parameter.Value --output text"
}
