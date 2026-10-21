resource "aws_ecr_repository" "api" {
  name                 = "${var.proyecto}-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

# Conserva solo las 2 imágenes más recientes (cuota gratuita de 500 MB).
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Conservar las 2 imagenes mas recientes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 2
      }
      action = { type = "expire" }
    }]
  })
}
