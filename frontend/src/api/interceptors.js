/**
 * Configuração de interceptores para axios
 * - Adicionar JWT ao header
 * - Tratar erros de forma centralizada
 * - Refresh token automaticamente
 */

export const setupInterceptors = (client) => {
  // Interceptor de requisição
  client.interceptors.request.use(
    (config) => {
      // Adicionar token JWT se existir
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Adicionar headers padrão
      config.headers['Content-Type'] = 'application/json';
      config.headers['X-Requested-With'] = 'XMLHttpRequest';

      return config;
    },
    (error) => {
      console.error('Erro ao preparar requisição:', error);
      return Promise.reject(error);
    }
  );

  // Interceptor de resposta
  client.interceptors.response.use(
    (response) => {
      return response;
    },
    async (error) => {
      const originalRequest = error.config;

      // Tratamento de erro 401 (Não autorizado)
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;

        try {
          // Tentar renovar o token
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken) {
            const response = await client.post('/auth/refresh-token', {
              refresh_token: refreshToken,
            });

            const { access_token, refresh_token: newRefreshToken } = response.data;
            
            // Atualizar tokens no localStorage
            localStorage.setItem('access_token', access_token);
            if (newRefreshToken) {
              localStorage.setItem('refresh_token', newRefreshToken);
            }

            // Repetir requisição original com novo token
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return client(originalRequest);
          } else {
            // Sem refresh token, redirecionar para login
            window.location.href = '/login';
            localStorage.clear();
          }
        } catch (refreshError) {
          console.error('Erro ao renovar token:', refreshError);
          // Redirecionar para login se falhar refresh
          window.location.href = '/login';
          localStorage.clear();
          return Promise.reject(refreshError);
        }
      }

      // Tratamento de erro 403 (Proibido)
      if (error.response?.status === 403) {
        console.error('Acesso proibido. Você não tem permissão para acessar este recurso.');
      }

      // Tratamento de erro 404 (Não encontrado)
      if (error.response?.status === 404) {
        console.error('Recurso não encontrado.');
      }

      // Tratamento de erro 500 (Erro do servidor)
      if (error.response?.status >= 500) {
        console.error('Erro no servidor. Por favor, tente novamente mais tarde.');
      }

      // Tratamento de erro de rede
      if (!error.response) {
        console.error('Erro de rede. Verifique sua conexão com a internet.');
      }

      return Promise.reject(error);
    }
  );
};
