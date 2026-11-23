output "alb_dns_name" {
  description = "Public Application Load Balancer DNS Endpoint"
  value       = aws_lb.main.dns_name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL 17 Endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis Primary Cluster Endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "ecs_cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.main.name
}
