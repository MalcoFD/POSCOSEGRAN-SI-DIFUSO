# Amplify compila el frontend desde GitHub con amplify.yml (raíz del repo) y lo
# publica en https://<rama>.<id>.amplifyapp.com. Cada push a la rama lo reconstruye.
resource "aws_amplify_app" "web" {
  name         = var.proyecto
  repository   = var.github_repo_url
  access_token = var.github_token
  platform     = "WEB"

  environment_variables = {
    VITE_AUTH_MODE = "local"
    VITE_API_URL   = "${aws_apigatewayv2_api.api.api_endpoint}/api/v1"
  }

  # SPA: toda ruta sin extensión de archivo estático sirve index.html.
  custom_rule {
    source = "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>"
    target = "/index.html"
    status = "200"
  }
}

resource "aws_amplify_branch" "principal" {
  app_id            = aws_amplify_app.web.id
  branch_name       = var.rama
  framework         = "React"
  stage             = "PRODUCTION"
  enable_auto_build = true
}
