import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios';

export interface ApiProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  invalid_params?: any;
}

export class NormalizedApiError extends Error {
  public problem: ApiProblemDetails;

  constructor(problem: ApiProblemDetails) {
    super(problem.detail || problem.title);
    this.name = 'NormalizedApiError';
    this.problem = problem;
  }
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json, application/problem+json',
  },
});

// Single source of truth: attach Bearer token on every outgoing request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('deva_access_token');
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<any>) => {
    if (error.response && error.response.data) {
      const data = error.response.data;
      const problem: ApiProblemDetails = {
        type: data.type || 'about:blank',
        title: data.title || error.message,
        status: error.response.status,
        detail: data.detail || error.message,
        instance: data.instance,
        invalid_params: data.invalid_params,
      };
      return Promise.reject(new NormalizedApiError(problem));
    }

    const networkProblem: ApiProblemDetails = {
      type: 'urn:problem:network-error',
      title: 'Network or Connection Error',
      status: 0,
      detail: error.message || 'Unable to reach backend API gateway',
    };
    return Promise.reject(new NormalizedApiError(networkProblem));
  }
);
