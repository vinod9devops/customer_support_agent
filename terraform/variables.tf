variable "region" {
  description = "AWS region"
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  default     = "cft-support-agent"
}

variable "allowed_prefix_list_id" {
  description = "Prefix list ID for developer access"
  default     = ""
}

variable "allowed_cidr_blocks" {
  description = "Additional CIDR blocks allowed to access the ALB"
  type        = list(string)
  default     = []
}

variable "ecr_image_tag" {
  description = "ECR image tag"
  default     = "latest"
}

variable "container_cpu" {
  description = "Fargate task CPU (1024 = 1 vCPU)"
  default     = 1024
}

variable "container_memory" {
  description = "Fargate task memory in MB"
  default     = 2048
}
