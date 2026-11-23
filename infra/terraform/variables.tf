variable "aws_region" {
  type        = string
  description = "AWS deployment region"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (production, staging)"
  default     = "production"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block"
  default     = "10.0.0.0/16"
}

variable "db_instance_class" {
  type        = string
  description = "RDS instance class for PostgreSQL"
  default     = "db.r6g.xlarge"
}

variable "db_password" {
  type        = string
  description = "PostgreSQL administrator master password"
  sensitive   = true
  default     = "deva_secure_prod_password_2026"
}

variable "redis_node_type" {
  type        = string
  description = "ElastiCache Redis node type"
  default     = "cache.r6g.large"
}
