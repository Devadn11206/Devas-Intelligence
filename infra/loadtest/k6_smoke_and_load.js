import http from 'k6/http';
import { check, group, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '15s', target: 5 },   // Ramp up
    { duration: '30s', target: 20 },  // Sustained load
    { duration: '15s', target: 0 },   // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1200'], // 95% of requests must complete below 500ms
    'http_req_failed': ['rate<0.01'],                  // HTTP failure rate below 1%
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

export default function () {
  group('Health & Readiness', () => {
    const res = http.get(`${BASE_URL}/api/v1/health/ready`);
    check(res, {
      'status is 200': (r) => r.status === 200,
      'db is healthy': (r) => {
        try {
          return JSON.parse(r.body).database === 'healthy';
        } catch (_) {
          return false;
        }
      },
    });
  });

  group('Intel Feed Retrieval', () => {
    const res = http.get(`${BASE_URL}/api/v1/intel/feed?limit=15`);
    check(res, {
      'feed status 200': (r) => r.status === 200,
      'feed has documents': (r) => {
        try {
          const body = JSON.parse(r.body);
          return Array.isArray(body.items || body.documents || body);
        } catch (_) {
          return false;
        }
      },
    });
  });

  group('Hybrid Search Execution', () => {
    const payload = JSON.stringify({
      query: 'Physics Informed Neural Networks PINNs',
      limit: 10,
      mode: 'hybrid',
    });
    const params = {
      headers: {
        'Content-Type': 'application/json',
      },
    };
    const res = http.post(`${BASE_URL}/api/v1/search`, payload, params);
    check(res, {
      'search status 200': (r) => r.status === 200,
      'search latency < 800ms': (r) => r.timings.duration < 800,
    });
  });

  group('Multi-Item Comparison Engine', () => {
    // Probe comparison endpoint with sample parameters
    const res = http.get(`${BASE_URL}/api/v1/intel/compare?ids=00000000-0000-0000-0000-000000000001,00000000-0000-0000-0000-000000000002`);
    check(res, {
      'compare responds without 500': (r) => r.status !== 500,
    });
  });

  sleep(1);
}
