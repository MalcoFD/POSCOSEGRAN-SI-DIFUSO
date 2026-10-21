variable "region" {
  description = "Región AWS. Debe ofrecer Amplify Hosting y db.t4g.micro en free tier."
  type        = string
  default     = "us-east-1"
}

variable "perfil_aws" {
  description = "Perfil de AWS CLI con el que se despliega (null usa las credenciales por defecto)."
  type        = string
  default     = null
}

variable "proyecto" {
  description = "Prefijo de nombres de recursos."
  type        = string
  default     = "poscosegran"
}

variable "github_repo_url" {
  description = "URL HTTPS del repositorio que Amplify compila."
  type        = string
  default     = "https://github.com/MalcoFD/POSCOSEGRAN-SI-DIFUSO"
}

variable "github_token" {
  description = "PAT de GitHub para que Amplify clone el repositorio y registre el webhook."
  type        = string
  sensitive   = true
}

variable "rama" {
  description = "Rama que Amplify publica."
  type        = string
  default     = "main"
}

variable "alerta_email" {
  description = "Correo que recibe las alertas del presupuesto."
  type        = string
}

variable "presupuesto_usd" {
  description = "Límite mensual del presupuesto de alerta, en USD."
  type        = number
  default     = 5
}

variable "db_instance_class" {
  description = "Clase de RDS. db.t4g.micro y db.t3.micro entran en el free tier."
  type        = string
  default     = "db.t4g.micro"
}

variable "api_imagen_tag" {
  description = "Etiqueta de la imagen de la API en ECR."
  type        = string
  default     = "latest"
}

variable "api_tareas" {
  description = "Tareas Fargate de la API. Poner 0 detiene el cómputo sin destruir nada."
  type        = number
  default     = 1
}
