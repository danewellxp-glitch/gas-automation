/**
 * Cliente axios configurado
 * - Endpoint base configurável
 * - Interceptores para JWT
 * - Tratamento de erros centralizado
 * - Timeout padrão
 */

import axios from 'axios';
import { setupInterceptors } from './interceptors';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://192.168.10.156:8000',
  timeout: 30000, // 30 segundos
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Configurar interceptores
setupInterceptors(apiClient);

export default apiClient;
