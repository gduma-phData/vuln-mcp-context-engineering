resource "aws_ecr_repository" "api" {
  name                 = "vuln-mcp-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "vuln-mcp-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "api_ecr_url" {
  value = aws_ecr_repository.api.repository_url
}

output "frontend_ecr_url" {
  value = aws_ecr_repository.frontend.repository_url
}
