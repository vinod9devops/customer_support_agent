output "alb_url" {
  description = "Application URL"
  value       = "http://${aws_lb.app.dns_name}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing images"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_exec_command" {
  description = "Command to exec into the running container"
  value       = "aws ecs execute-command --cluster ${var.project_name} --task <TASK_ID> --container ${var.project_name} --interactive --command /bin/bash --region ${var.region}"
}

output "update_secrets_hint" {
  description = "Run this to update secrets after deploy"
  value       = "cd ../deploy && ./update-secrets.sh ${var.region}"
}

output "get_task_id_command" {
  description = "Get running task ID"
  value       = "aws ecs list-tasks --cluster ${var.project_name} --service-name ${var.project_name} --query 'taskArns[0]' --output text --region ${var.region}"
}
