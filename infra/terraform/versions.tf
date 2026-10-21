terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Estado local: contiene contraseñas generadas. No se sube al repositorio
  # (ver .gitignore). Para una demo de pocos días no compensa un backend S3.
}

provider "aws" {
  region  = var.region
  profile = var.perfil_aws

  default_tags {
    tags = {
      Proyecto = var.proyecto
      Gestion  = "terraform"
    }
  }
}

data "aws_caller_identity" "actual" {}
data "aws_region" "actual" {}
data "aws_availability_zones" "disponibles" {
  state = "available"
}
