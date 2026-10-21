#Requires -Version 5.1
<#
Despliegue temporal en AWS (infra/terraform): aplica Terraform, publica la imagen
de la API en ECR, redespliega ECS Fargate y lanza el build de Amplify.
Requiere Terraform, AWS CLI v2 y Docker Desktop iniciado.
#>
[CmdletBinding()]
param(
    [string]$Perfil = "",
    [switch]$SaltarTerraform,
    [switch]$SaltarFrontend
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$tfDir = Join-Path $projectRoot "infra/terraform"
$perfilArgs = if ($Perfil) { @("--profile", $Perfil) } else { @() }

function Invoke-Paso([string]$descripcion, [scriptblock]$accion) {
    Write-Host "==> $descripcion" -ForegroundColor Cyan
    & $accion
    if ($LASTEXITCODE -ne 0) { throw "Falló: $descripcion" }
}

function Get-Salida([string]$nombre) {
    $valor = & terraform "-chdir=$tfDir" output -raw $nombre
    if ($LASTEXITCODE -ne 0) { throw "No existe la salida de Terraform '$nombre'." }
    return $valor
}

if (-not $SaltarTerraform) {
    Invoke-Paso "terraform init" { terraform "-chdir=$tfDir" init -input=false }
    Invoke-Paso "terraform apply" { terraform "-chdir=$tfDir" apply }
}

$region = Get-Salida "region"
$repo = Get-Salida "ecr_repo_url"
$cluster = Get-Salida "ecs_cluster"
$servicio = Get-Salida "ecs_servicio"
$registro = $repo.Split("/")[0]

Invoke-Paso "docker login en ECR" {
    aws ecr get-login-password --region $region @perfilArgs | docker login --username AWS --password-stdin $registro
}
Push-Location $projectRoot
try {
    Invoke-Paso "docker build de la API" {
        docker build --platform linux/amd64 -f backend/Dockerfile -t "${repo}:latest" .
    }
} finally {
    Pop-Location
}
Invoke-Paso "docker push" { docker push "${repo}:latest" }

Invoke-Paso "redesplegar ECS" {
    aws ecs update-service --region $region @perfilArgs --cluster $cluster --service $servicio --force-new-deployment --query "service.serviceName" --output text
}
Write-Host "Esperando a que el servicio se estabilice (inicializar + api)..."
Invoke-Paso "esperar ECS" {
    aws ecs wait services-stable --region $region @perfilArgs --cluster $cluster --services $servicio
}

if (-not $SaltarFrontend) {
    $appId = Get-Salida "amplify_app_id"
    $rama = Get-Salida "amplify_rama"
    Invoke-Paso "build de Amplify" {
        aws amplify start-job --region $region @perfilArgs --app-id $appId --branch-name $rama --job-type RELEASE --query "jobSummary.jobId" --output text
    }
}

Write-Host ""
Write-Host "Frontend: $(Get-Salida 'frontend_url')  (el build de Amplify tarda ~3-5 min)"
Write-Host "API:      $(Get-Salida 'api_url')/salud/bd"
Write-Host "Contraseña de los usuarios de demo:"
Write-Host "  $(Get-Salida 'comando_password_login')"
