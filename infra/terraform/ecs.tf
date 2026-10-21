resource "aws_ecs_cluster" "principal" {
  name = var.proyecto
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.proyecto}-api"
  retention_in_days = 3
}

# --- Rol de ejecución: descarga la imagen, escribe logs y lee los secretos de SSM.
data "aws_iam_policy_document" "ecs_asumir" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ejecucion" {
  name               = "${var.proyecto}-ecs-ejecucion"
  assume_role_policy = data.aws_iam_policy_document.ecs_asumir.json
}

resource "aws_iam_role_policy_attachment" "ejecucion_base" {
  role       = aws_iam_role.ejecucion.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ejecucion_secretos" {
  statement {
    actions   = ["ssm:GetParameters"]
    resources = [for p in aws_ssm_parameter.secreto : p.arn]
  }
  statement {
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${data.aws_region.actual.name}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "ejecucion_secretos" {
  name   = "leer-secretos"
  role   = aws_iam_role.ejecucion.id
  policy = data.aws_iam_policy_document.ejecucion_secretos.json
}

# --- Descubrimiento: API Gateway llega a la tarea por Cloud Map (registro SRV),
# así no hace falta un ALB aunque la IP de la tarea cambie en cada despliegue.
resource "aws_service_discovery_private_dns_namespace" "principal" {
  name = "${var.proyecto}.interno"
  vpc  = aws_vpc.principal.id
}

resource "aws_service_discovery_service" "api" {
  name = "api"

  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.principal.id
    routing_policy = "MULTIVALUE"

    dns_records {
      type = "SRV"
      ttl  = 10
    }
  }
}

# --- Tarea: "inicializar" (equivalente al servicio homónimo de compose.yaml)
# migra, crea roles y usuarios de demo y carga la base de conocimiento; es
# idempotente, así que corre en cada arranque. La API espera a que termine bien.
locals {
  imagen_api = "${aws_ecr_repository.api.repository_url}:${var.api_imagen_tag}"
  origen_web = "https://${var.rama}.${aws_amplify_app.web.default_domain}"

  entorno_comun = [
    { name = "POSCOSEGRAN_ENTORNO", value = "pruebas" },
    { name = "POSCOSEGRAN_JWT_MODO", value = "SECRETO_COMPARTIDO" },
    { name = "POSCOSEGRAN_JWT_ALGORITMOS", value = "HS256" },
    { name = "POSCOSEGRAN_JWT_EMISOR", value = "${var.proyecto}-aws" },
    { name = "POSCOSEGRAN_AUTH_LOCAL_HABILITADA", value = "true" },
  ]

  secretos_comunes = [
    { name = "POSCOSEGRAN_BD_URL_APP", valueFrom = aws_ssm_parameter.secreto["bd_url_app"].arn },
    { name = "POSCOSEGRAN_JWT_SECRETO", valueFrom = aws_ssm_parameter.secreto["jwt_secreto"].arn },
    { name = "POSCOSEGRAN_AUTH_LOCAL_PASSWORD", valueFrom = aws_ssm_parameter.secreto["auth_local_password"].arn },
  ]

  logs = {
    logDriver = "awslogs"
    options = {
      awslogs-group         = aws_cloudwatch_log_group.api.name
      awslogs-region        = data.aws_region.actual.name
      awslogs-stream-prefix = "ecs"
    }
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.proyecto}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ejecucion.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name             = "inicializar"
      image            = local.imagen_api
      essential        = false
      command          = ["python", "scripts/preparar_local.py", "--contenedor"]
      environment      = local.entorno_comun
      logConfiguration = local.logs
      secrets = concat(local.secretos_comunes, [
        { name = "POSCOSEGRAN_BD_URL_ADMIN_LOCAL", valueFrom = aws_ssm_parameter.secreto["bd_url_admin"].arn },
        { name = "POSCOSEGRAN_BD_URL_MIGRACIONES", valueFrom = aws_ssm_parameter.secreto["bd_url_migraciones"].arn },
        { name = "POSCOSEGRAN_BD_PASSWORD_APP", valueFrom = aws_ssm_parameter.secreto["bd_password_app"].arn },
        { name = "POSCOSEGRAN_BD_PASSWORD_MIGRACIONES", valueFrom = aws_ssm_parameter.secreto["bd_password_migraciones"].arn },
      ])
    },
    {
      name      = "api"
      image     = local.imagen_api
      essential = true
      # --proxy-headers: el límite de intentos de login usa la IP real del
      # cliente que API Gateway envía en X-Forwarded-For.
      command = [
        "uvicorn", "poscosegran.api.app:crear_app", "--factory",
        "--host", "0.0.0.0", "--port", "8000",
        "--proxy-headers", "--forwarded-allow-ips", "*",
      ]
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      dependsOn    = [{ containerName = "inicializar", condition = "SUCCESS" }]
      environment = concat(local.entorno_comun, [
        { name = "POSCOSEGRAN_CORS_ORIGENES", value = local.origen_web },
        { name = "POSCOSEGRAN_BD_POOL_TAMANO", value = "3" },
        { name = "POSCOSEGRAN_BD_POOL_DESBORDE", value = "2" },
        { name = "POSCOSEGRAN_LIMITE_PETICIONES_POR_MINUTO", value = "300" },
        { name = "POSCOSEGRAN_LIMITE_PETICIONES_ESCRITURA_POR_MINUTO", value = "100" },
      ])
      secrets          = local.secretos_comunes
      logConfiguration = local.logs
      healthCheck = {
        command     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/salud/bd')"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    },
  ])
}

resource "aws_ecs_service" "api" {
  name            = "${var.proyecto}-api"
  cluster         = aws_ecs_cluster.principal.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_tareas
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.publica[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn   = aws_service_discovery_service.api.arn
    container_name = "api"
    container_port = 8000
  }

  # En el primer apply ECR todavía está vacío: no esperar a que el servicio
  # se estabilice. scripts/desplegar_aws.ps1 publica la imagen y lo redespliega.
  wait_for_steady_state = false
}
