# ==============================================================================
# Managed Storage: RDS PostgreSQL 17 (pgvector) & ElastiCache Redis 7
# ==============================================================================

resource "aws_db_subnet_group" "rds" {
  name       = "deva-${var.environment}-rds-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

resource "aws_security_group" "rds" {
  name        = "deva-${var.environment}-rds-sg"
  description = "Allow inbound postgres traffic from ECS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "deva-${var.environment}-db"
  allocated_storage      = 100
  max_allocated_storage  = 1000
  engine                 = "postgres"
  engine_version         = "17.1"
  instance_class         = var.db_instance_class
  db_name                = "deva_db"
  username               = "deva_admin"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  skip_final_snapshot    = true
  multi_az               = true
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "deva-${var.environment}-redis-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

resource "aws_security_group" "redis" {
  name        = "deva-${var.environment}-redis-sg"
  description = "Allow inbound Redis traffic from ECS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "deva-${var.environment}-redis"
  description                = "DEVA Intelligence Redis cluster"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 2
  parameter_group_name       = "default.redis7"
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  automatic_failover_enabled = true
}
