/**
 * Logger centralizado para o frontend.
 * 
 * Em desenvolvimento: Loga tudo no console
 * Em produção: Silencia logs de debug/info, mantém apenas errors/warnings
 * 
 * Uso:
 *   import logger from '@/utils/logger'
 *   logger.log('Mensagem de debug')
 *   logger.error('Erro crítico', error)
 */

const isDev = import.meta.env.MODE === 'development' || import.meta.env.DEV

const logger = {
  /**
   * Log de debug - Apenas em desenvolvimento
   * Use para informações detalhadas de debugging
   */
  log: (...args) => {
    if (isDev) {
      console.log('[LOG]', new Date().toISOString(), ...args)
    }
  },

  /**
   * Log de informação - Apenas em desenvolvimento
   * Use para informações gerais do fluxo da aplicação
   */
  info: (...args) => {
    if (isDev) {
      console.info('[INFO]', new Date().toISOString(), ...args)
    }
  },

  /**
   * Log de debug detalhado - Apenas em desenvolvimento
   * Use para informações muito verbosas
   */
  debug: (...args) => {
    if (isDev) {
      console.debug('[DEBUG]', new Date().toISOString(), ...args)
    }
  },

  /**
   * Warning - Sempre loga
   * Use para avisos que não impedem funcionamento
   */
  warn: (...args) => {
    console.warn('[WARN]', new Date().toISOString(), ...args)
  },

  /**
   * Error - Sempre loga
   * Use para erros que precisam atenção
   * 
   * Em produção, considere enviar para serviço de tracking
   * (Sentry, LogRocket, etc)
   */
  error: (...args) => {
    console.error('[ERROR]', new Date().toISOString(), ...args)
    
    // TODO: Em produção, enviar para serviço de error tracking
    // if (!isDev) {
    //   Sentry.captureException(args[0])
    // }
  },

  /**
   * Helper para criar grupos de logs colapsáveis
   */
  group: (title, ...args) => {
    if (isDev) {
      console.group(title)
      args.forEach(arg => console.log(arg))
      console.groupEnd()
    }
  },

  /**
   * Helper para medir performance
   */
  time: (label) => {
    if (isDev) {
      console.time(label)
    }
  },

  timeEnd: (label) => {
    if (isDev) {
      console.timeEnd(label)
    }
  },
}

// IMPORTANTE: Nunca logue dados sensíveis!
// ❌ ERRADO:
//   logger.log('Token:', token)
//   logger.log('Password:', password)
//   logger.log('Customer data:', customer)
//
// ✅ CORRETO:
//   logger.log('Token validado com sucesso')
//   logger.log('Login realizado')
//   logger.log('Customer ID:', customer.id)

export default logger
