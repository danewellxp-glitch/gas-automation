"""
Enhanced Chatbot Service - Multi-tier AI with Claude, Ollama, and Fallback
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlmodel import Session, select
from app.models.auth_models import Message, Conversation, BotContext, brazilian_now
from app.integrations.ollama import OllamaClient

# Try to import anthropic for Claude API
try:
    import anthropic
except ImportError:
    anthropic = None


class DatabaseContextManager:
    """Manages conversation context with database persistence"""

    def __init__(self, session: Session):
        self.session = session
        self.context_timeout = timedelta(hours=2)

    def get_context(self, phone_number: str) -> Dict:
        """Get conversation context for a phone number from database"""
        context_record = self.session.exec(
            select(BotContext).where(BotContext.phone_number == phone_number)
        ).first()

        if context_record:
            # Check if context is still valid (handle timezone comparison)
            current_time = brazilian_now()
            try:
                is_valid = context_record.expires_at > current_time
            except TypeError:
                # Handle timezone-aware vs naive datetime comparison
                if context_record.expires_at.tzinfo is None:
                    is_valid = context_record.expires_at > current_time.replace(tzinfo=None)
                else:
                    is_valid = context_record.expires_at > current_time

            if is_valid:
                # Parse collected_info if it's a JSON string
                collected_info = context_record.collected_info
                if isinstance(collected_info, str):
                    try:
                        collected_info = json.loads(collected_info)
                    except (json.JSONDecodeError, TypeError):
                        collected_info = {}

                return {
                    'phone_number': phone_number,
                    'conversation_stage': context_record.conversation_stage,
                    'user_intent': context_record.user_intent,
                    'collected_info': collected_info,
                    'bot_responses_count': context_record.bot_responses_count,
                    'escalation_requested': context_record.escalation_requested,
                    'escalation_reason': context_record.escalation_reason,
                    'last_updated': context_record.last_updated,
                    'user_last_message': None,
                    'last_bot_response': None
                }
            else:
                # Context expired, delete it
                self.session.delete(context_record)
                self.session.commit()

        # Create new context
        new_context = {
            'phone_number': phone_number,
            'conversation_stage': 'greeting',
            'user_intent': None,
            'collected_info': {},
            'bot_responses_count': 0,
            'escalation_requested': False,
            'escalation_reason': None,
            'last_updated': brazilian_now(),
            'user_last_message': None,
            'last_bot_response': None
        }

        self._save_context_to_db(phone_number, new_context)
        return new_context

    def update_context(self, phone_number: str, updates: Dict):
        """Update conversation context in database"""
        context_record = self.session.exec(
            select(BotContext).where(BotContext.phone_number == phone_number)
        ).first()

        if not context_record:
            context_record = BotContext(phone_number=phone_number)
            self.session.add(context_record)

        # Update fields
        if 'conversation_stage' in updates:
            context_record.conversation_stage = updates['conversation_stage']
        if 'user_intent' in updates:
            context_record.user_intent = updates['user_intent']
        if 'collected_info' in updates:
            info = updates['collected_info']
            context_record.collected_info = json.dumps(info) if isinstance(info, dict) else str(info)
        if 'bot_responses_count' in updates:
            context_record.bot_responses_count = updates['bot_responses_count']
        if 'escalation_requested' in updates:
            context_record.escalation_requested = updates['escalation_requested']
        if 'escalation_reason' in updates:
            context_record.escalation_reason = updates['escalation_reason']

        context_record.last_updated = brazilian_now()
        context_record.expires_at = brazilian_now() + self.context_timeout

        self.session.commit()

    def _save_context_to_db(self, phone_number: str, context: Dict):
        """Save new context to database"""
        collected_info = context.get('collected_info', {})
        if isinstance(collected_info, dict):
            collected_info = json.dumps(collected_info)

        context_record = BotContext(
            phone_number=phone_number,
            conversation_stage=context.get('conversation_stage', 'greeting'),
            user_intent=context.get('user_intent'),
            collected_info=collected_info,
            bot_responses_count=context.get('bot_responses_count', 0),
            escalation_requested=context.get('escalation_requested', False),
            escalation_reason=context.get('escalation_reason'),
            last_updated=context.get('last_updated', brazilian_now()),
            expires_at=brazilian_now() + self.context_timeout
        )
        self.session.add(context_record)
        self.session.commit()

    def clear_context(self, phone_number: str):
        """Clear context for a phone number"""
        context_record = self.session.exec(
            select(BotContext).where(BotContext.phone_number == phone_number)
        ).first()
        if context_record:
            self.session.delete(context_record)
            self.session.commit()

    def cleanup_expired_contexts(self) -> int:
        """Clean up expired contexts from database"""
        current_time = brazilian_now()

        try:
            expired_contexts = self.session.exec(
                select(BotContext).where(BotContext.expires_at < current_time)
            ).all()
        except TypeError:
            expired_contexts = self.session.exec(
                select(BotContext).where(BotContext.expires_at < current_time.replace(tzinfo=None))
            ).all()

        count = len(expired_contexts)
        for context in expired_contexts:
            self.session.delete(context)

        self.session.commit()
        return count


class ClaudeChatbotRouter:
    """Enhanced routing logic with Claude-specific considerations"""

    # Keywords that indicate user wants human help
    ESCALATION_KEYWORDS = [
        'falar com atendente', 'atendente', 'operador', 'humano', 'pessoa',
        'talk to agent', 'agent', 'human', 'operator', 'representative',
        'urgente', 'urgent', 'problema grave', 'serious problem',
        'reclamacao', 'reclamacaoo', 'complaint', 'insatisfeito', 'dissatisfied'
    ]

    # Complex intents that should go to humans
    COMPLEX_INTENTS = [
        'refund', 'reembolso', 'cancelamento', 'cancel', 'estorno',
        'problema tecnico', 'technical issue', 'bug', 'falha',
        'conta bloqueada', 'account blocked', 'login problem',
        'cobranca incorreta', 'billing issue', 'pagamento'
    ]

    # Topics the bot handles well
    BOT_CAPABLE_INTENTS = [
        'horario', 'hours', 'funcionamento', 'operating',
        'preco', 'price', 'valor', 'cost', 'quanto custa',
        'informacao', 'information', 'sobre', 'about',
        'contato', 'contact', 'telefone', 'email',
        'localizacao', 'location', 'endereco', 'address',
        'duvida', 'question', 'ajuda', 'help'
    ]

    def should_escalate_to_human(self, message: str, context: Dict) -> Tuple[bool, str]:
        """Determine if message should be escalated to human agent"""
        message_lower = message.lower()

        # Direct escalation request
        if any(keyword in message_lower for keyword in self.ESCALATION_KEYWORDS):
            return True, "user_requested"

        # Too many bot responses without resolution
        if context.get('bot_responses_count', 0) >= 5:
            return True, "max_bot_responses"

        # Complex intents that need human help
        if any(intent in message_lower for intent in self.COMPLEX_INTENTS):
            return True, "complex_intent"

        # User expressed frustration
        frustration_words = ['nao entendi', 'nao funciona', 'frustrado', 'irritado', 'confused', 'frustrated', 'nao resolve', 'nao ajuda']
        if any(word in message_lower for word in frustration_words):
            return True, "user_frustration"

        # Previous escalation was requested
        if context.get('escalation_requested'):
            return True, "previous_escalation"

        # Check for business hours (can be configured)
        current_hour = brazilian_now().hour
        business_start = int(os.getenv("BUSINESS_HOURS_START", "8"))
        business_end = int(os.getenv("BUSINESS_HOURS_END", "18"))

        if current_hour < business_start or current_hour >= business_end:
            if any(intent in message_lower for intent in self.COMPLEX_INTENTS):
                return True, "outside_business_hours"

        return False, "bot_can_handle"


class PermanentFallbackBot:
    """Rule-based permanent chatbot that works without external services"""

    def __init__(self):
        self.greeting_responses = [
            "Ola! Como posso ajuda-lo hoje?",
            "Ola! Bem-vindo! Em que posso ser util?",
            "Oi! Fico feliz em atende-lo! Como posso ajudar?"
        ]

        self.business_hours_info = """
Nossos horarios de atendimento:

Segunda a Sexta: 8h as 18h
Sabado: 8h as 12h
Domingo: Fechado

Fora desses horarios, deixe sua mensagem que retornaremos assim que possivel!
"""

        self.contact_info = """
Nossos contatos:

WhatsApp: Este numero que voce esta usando
Telefone: (41) 3333-4444
Email: contato@gasautomation.com.br

Estou aqui para ajudar no que precisar!
"""

        self.menu_info = """
*Nossos Produtos:*

*P13* (13kg)
  Com troca: R$ 100,00
  Sem troca: R$ 110,00

*P20* (20kg)
  Com troca: R$ 165,00
  Sem troca: R$ 180,00

*P45* (45kg)
  Com troca: R$ 320,00
  Sem troca: R$ 350,00

Para fazer um pedido, digite *PEDIR* ou aguarde um atendente!
"""

        self.faq_responses = {
            'horario': self.business_hours_info,
            'funcionamento': self.business_hours_info,
            'contato': self.contact_info,
            'telefone': self.contact_info,
            'email': self.contact_info,
            'endereco': self.contact_info,
            'preco': self.menu_info,
            'valor': self.menu_info,
            'cardapio': self.menu_info,
            'menu': self.menu_info,
            'produtos': self.menu_info,
        }

    def get_response(self, message: str, profile_name: str = "Cliente", context: Dict = None) -> str:
        """Generate rule-based response"""
        message_lower = message.lower().strip()

        # Handle greetings
        if any(word in message_lower for word in ['oi', 'ola', 'hello', 'hi', 'bom dia', 'boa tarde', 'boa noite']):
            greeting = f"Ola {profile_name}! "

            if context and context.get('bot_responses_count', 0) > 0:
                greeting += "Que bom ter voce de volta! "
            else:
                greeting += "Bem-vindo! "

            greeting += """Como posso ajuda-lo hoje?

- Horarios de atendimento
- Precos e produtos
- Informacoes de contato
- Fazer pedido

Ou digite 'atendente' para falar com nossa equipe!"""
            return greeting

        # Handle thanks
        if any(word in message_lower for word in ['obrigado', 'obrigada', 'valeu', 'thanks']):
            return f"Por nada, {profile_name}! Fico feliz em ajudar! Se precisar de mais alguma coisa, estarei aqui!"

        # Handle FAQ topics
        for keyword, response in self.faq_responses.items():
            if keyword in message_lower:
                return response

        # Handle problems/issues
        if any(word in message_lower for word in ['problema', 'erro', 'nao funciona', 'bug', 'defeito']):
            return f"Entendo que voce esta com um problema, {profile_name}. Para resolver isso da melhor forma, vou conectar voce com nosso suporte tecnico. Digite 'atendente' para continuar."

        # Handle complaints
        if any(word in message_lower for word in ['reclamacao', 'insatisfeito', 'ruim', 'pessimo']):
            return f"Lamento que tenha tido uma experiencia negativa, {profile_name}. Sua opiniao e muito importante. Vou conectar voce com um supervisor. Digite 'atendente'."

        # Default helpful response
        responses = [
            f"Recebi sua mensagem, {profile_name}! Para ajuda-lo melhor, posso conecta-lo com um atendente. Digite 'atendente' ou me diga como posso ajudar com:\n\n- Horarios\n- Precos\n- Contato",
            f"Obrigado pela mensagem, {profile_name}! Posso ajudar com informacoes basicas ou conecta-lo com um especialista. Digite 'atendente' para falar com nossa equipe!",
            f"Entendi, {profile_name}! Para melhor atende-lo, posso conectar voce com um atendente humano. Digite 'atendente' ou me diga sobre o que gostaria de saber!"
        ]

        response_index = context.get('bot_responses_count', 0) % len(responses) if context else 0
        return responses[response_index]


class EnhancedClaudeChatbotService:
    """Enhanced chatbot service with Claude API, Ollama, and permanent fallbacks"""

    def __init__(self, session: Session):
        self.session = session
        self.context_manager = DatabaseContextManager(session)
        self.router = ClaudeChatbotRouter()
        self.fallback_bot = PermanentFallbackBot()
        self.ollama_client = OllamaClient()

        # Initialize Claude client
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_client = None
        if self.claude_api_key and anthropic:
            try:
                self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
                print("Claude API initialized successfully")
            except Exception as e:
                print(f"Failed to initialize Claude API: {e}")
        elif not anthropic:
            print("Anthropic package not available - Claude chatbot disabled")
        else:
            print("Claude API key not found - using Ollama/fallback bot only")

    async def process_message(self, phone_number: str, message: str, profile_name: str = "Cliente") -> Dict:
        """Process incoming message and determine appropriate response"""
        start_time = datetime.now()

        # Get conversation context from database
        context = self.context_manager.get_context(phone_number)

        # Check if should escalate to human
        should_escalate, escalation_reason = self.router.should_escalate_to_human(message, context)

        if should_escalate:
            self.context_manager.update_context(phone_number, {
                'escalation_requested': True,
                'escalation_reason': escalation_reason
            })

            escalation_message = self.get_escalation_message(escalation_reason, profile_name)

            return {
                'should_escalate': True,
                'escalation_reason': escalation_reason,
                'bot_response': escalation_message,
                'bot_service': 'escalation',
                'context_updated': True,
                'response_time_ms': int((datetime.now() - start_time).total_seconds() * 1000)
            }

        # Try to get bot response with multi-tier approach
        bot_response, bot_service = await self._get_multi_tier_response(message, context, profile_name)

        if bot_response:
            # Update context in database
            self.context_manager.update_context(phone_number, {
                'bot_responses_count': context.get('bot_responses_count', 0) + 1,
                'conversation_stage': self._determine_conversation_stage(message, context)
            })

            return {
                'should_escalate': False,
                'escalation_reason': None,
                'bot_response': bot_response,
                'bot_service': bot_service,
                'context_updated': True,
                'response_time_ms': int((datetime.now() - start_time).total_seconds() * 1000)
            }
        else:
            # Even fallback failed, escalate
            self.context_manager.update_context(phone_number, {
                'escalation_requested': True,
                'escalation_reason': 'all_bots_failed'
            })

            return {
                'should_escalate': True,
                'escalation_reason': 'all_bots_failed',
                'bot_response': self.get_escalation_message('all_bots_failed', profile_name),
                'bot_service': 'escalation',
                'context_updated': True,
                'response_time_ms': int((datetime.now() - start_time).total_seconds() * 1000)
            }

    async def _get_multi_tier_response(self, message: str, context: Dict, profile_name: str) -> Tuple[Optional[str], str]:
        """Multi-tier bot response system: Claude -> Ollama -> Permanent Fallback"""

        # Tier 1: Claude API (Primary)
        if self.claude_client:
            try:
                response = await self._try_claude_api(message, context, profile_name)
                if response:
                    return response, "claude"
            except Exception as e:
                print(f"Claude API failed: {e}")

        # Tier 2: Ollama (Secondary)
        try:
            response = await self._try_ollama(message, context, profile_name)
            if response:
                return response, "ollama"
        except Exception as e:
            print(f"Ollama failed: {e}")

        # Tier 3: Permanent Fallback (Always Available)
        response = self.fallback_bot.get_response(message, profile_name, context)
        return response, "fallback"

    async def _try_claude_api(self, message: str, context: Dict, profile_name: str) -> Optional[str]:
        """Try Claude API with enhanced context"""
        try:
            system_prompt = f"""Voce e um assistente virtual amigavel de uma loja de gas (botijao) brasileira.

Cliente: {profile_name}
Estagio da conversa: {context.get('conversation_stage', 'greeting')}
Respostas do bot anteriores: {context.get('bot_responses_count', 0)}

Instrucoes:
- Responda em Portugues (Brasileiro)
- Seja amigavel, util e profissional
- Mantenha respostas concisas (maximo 150 palavras)
- Se nao conseguir ajudar completamente, sugira falar com um atendente digitando 'atendente'
- Lide com perguntas comuns: horarios, contato, precos, produtos
- Para assuntos complexos (reembolsos, problemas tecnicos, cobrancas), recomende atendente humano
- Nossos produtos: P13 (13kg) R$100-110, P20 (20kg) R$165-180, P45 (45kg) R$320-350
- Horario: Seg-Sab 8h-18h, Dom 8h-12h
"""

            user_prompt = f"Mensagem do cliente: {message}"

            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            claude_response = response.content[0].text.strip()

            # Validate response
            if len(claude_response) > 10:
                return claude_response

            return None

        except Exception as e:
            print(f"Claude API error: {e}")
            return None

    async def _try_ollama(self, message: str, context: Dict, profile_name: str) -> Optional[str]:
        """Try to get response from Ollama"""
        try:
            prompt = f"""Voce e um assistente virtual amigavel de uma loja de gas.
Cliente: {profile_name}
Estagio: {context.get('conversation_stage', 'greeting')}
Mensagem: {message}

Responda de forma util e amigavel em portugues. Se for sobre pedidos, direcione para atendente humano.
Mantenha respostas curtas e diretas. Nossos produtos: P13 R$100, P20 R$165, P45 R$320."""

            response = await self.ollama_client.generate_response(prompt)
            return response.strip() if response else None
        except Exception as e:
            print(f"Ollama error: {e}")
            return None

    def _determine_conversation_stage(self, message: str, context: Dict) -> str:
        """Determine conversation stage based on message content"""
        message_lower = message.lower()

        if any(word in message_lower for word in ['oi', 'ola', 'hello', 'hi']):
            return 'greeting'
        elif any(word in message_lower for word in ['preco', 'valor', 'quanto custa', 'cardapio', 'menu']):
            return 'pricing_inquiry'
        elif any(word in message_lower for word in ['problema', 'erro', 'bug']):
            return 'support_request'
        elif any(word in message_lower for word in ['horario', 'funcionamento']):
            return 'info_request'
        elif any(word in message_lower for word in ['pedir', 'pedido', 'comprar', 'quero']):
            return 'order_intent'
        elif any(word in message_lower for word in ['obrigado', 'valeu', 'thanks']):
            return 'closing'
        else:
            return context.get('conversation_stage', 'general_inquiry')

    def get_escalation_message(self, escalation_reason: str, profile_name: str) -> str:
        """Get appropriate escalation message based on reason"""

        messages = {
            'user_requested': f"Perfeito, {profile_name}! Vou conectar voce com um de nossos atendentes. Um momento, por favor.",
            'max_bot_responses': f"Para melhor atende-lo, {profile_name}, vou conectar voce com um atendente especializado.",
            'complex_intent': f"Entendo que sua solicitacao e importante, {profile_name}. Vou conectar voce com um especialista que pode ajuda-lo melhor.",
            'user_frustration': f"Peco desculpas pela confusao, {profile_name}. Vou transferir voce para um atendente humano agora.",
            'previous_escalation': f"Como solicitado, {profile_name}, vou conectar voce com um atendente.",
            'outside_business_hours': f"Como estamos fora do horario comercial, {profile_name}, vou conectar voce com nosso atendente de plantao.",
            'all_bots_failed': f"Para garantir o melhor atendimento, {profile_name}, vou conectar voce com nossa equipe.",
            'bot_no_response': f"Para melhor atende-lo, {profile_name}, vou conectar voce com um de nossos atendentes."
        }

        return messages.get(escalation_reason, f"Vou conectar voce com um atendente, {profile_name}.")

    def cleanup_expired_contexts(self) -> int:
        """Clean up expired conversation contexts from database"""
        return self.context_manager.cleanup_expired_contexts()

    def clear_context(self, phone_number: str):
        """Clear context for a specific phone number"""
        self.context_manager.clear_context(phone_number)
