import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export type ComponentStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface ComponentHealth {
  status: ComponentStatus;
  latency_ms: number;
  error?: string;
  pgvector?: boolean;
  workers?: string[];
  message?: string;
}

export interface ReadyHealthResponse {
  status: ComponentStatus;
  timestamp: number;
  environment: string;
  components: {
    postgres: ComponentHealth;
    redis: ComponentHealth;
    celery: ComponentHealth;
  };
}

export interface LiveHealthResponse {
  status: string;
  version: string;
}

export const useSystemReadiness = () => {
  return useQuery<ReadyHealthResponse, Error>({
    queryKey: ['system', 'readiness'],
    queryFn: async () => {
      const { data } = await apiClient.get<ReadyHealthResponse>('/v1/health/ready');
      return data;
    },
    refetchInterval: 15000, // Poll every 15 seconds
    retry: 1,
    staleTime: 10000,
  });
};

export const useSystemLiveness = () => {
  return useQuery<LiveHealthResponse, Error>({
    queryKey: ['system', 'liveness'],
    queryFn: async () => {
      const { data } = await apiClient.get<LiveHealthResponse>('/v1/health/live');
      return data;
    },
    refetchInterval: 30000,
  });
};
