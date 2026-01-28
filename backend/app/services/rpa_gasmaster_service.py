"""
Serviço RPA para automação do Gasmaster (Windows Desktop).

Simula usuário digitando dados no sistema Gasmaster quando não há
permissão de escrita direta no banco Firebird.

Requisitos:
    pip install pyautogui pywinauto pillow

IMPORTANTE:
    - Este serviço deve rodar na mesma máquina onde o Gasmaster está instalado
    - O Gasmaster deve estar aberto e logado
    - Configurar as coordenadas/controles conforme a versão do Gasmaster
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID

logger = logging.getLogger(__name__)

# Tentar importar bibliotecas de automação
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    # Configurações de segurança
    pyautogui.FAILSAFE = True  # Mover mouse para canto para abortar
    pyautogui.PAUSE = 0.5  # Pausa entre ações
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui não disponível. Instale com: pip install pyautogui")

try:
    from pywinauto import Application, Desktop
    from pywinauto.keyboard import send_keys
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    logger.warning("pywinauto não disponível. Instale com: pip install pywinauto")


class RPAStatus(str, Enum):
    """Status da execução RPA."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    GASMASTER_NOT_FOUND = "gasmaster_not_found"
    SCREEN_NOT_FOUND = "screen_not_found"


@dataclass
class GasmasterConfig:
    """Configuração do Gasmaster para automação."""

    # Identificação da janela
    window_title: str = "Gasmaster"
    window_class: Optional[str] = None
    exe_path: Optional[str] = None

    # Timeouts (segundos)
    window_timeout: int = 10
    action_delay: float = 0.3
    typing_delay: float = 0.05

    # Coordenadas da tela de vendas (ajustar conforme Gasmaster)
    # Estas são coordenadas de exemplo - PRECISAM SER CONFIGURADAS
    screen_vendas: Dict[str, Any] = None

    def __post_init__(self):
        if self.screen_vendas is None:
            # Coordenadas padrão (EXEMPLO - ajustar para seu Gasmaster)
            self.screen_vendas = {
                "menu_vendas": {"x": 100, "y": 50},  # Menu Vendas
                "btn_nova_venda": {"x": 150, "y": 100},  # Botão Nova Venda
                "campo_cliente": {"x": 200, "y": 200},  # Campo código cliente
                "campo_produto": {"x": 200, "y": 250},  # Campo código produto
                "campo_quantidade": {"x": 350, "y": 250},  # Campo quantidade
                "campo_preco": {"x": 450, "y": 250},  # Campo preço
                "btn_adicionar_item": {"x": 550, "y": 250},  # Botão adicionar item
                "btn_finalizar": {"x": 400, "y": 500},  # Botão finalizar venda
                "btn_confirmar": {"x": 400, "y": 400},  # Botão confirmar
            }


@dataclass
class OrderToExport:
    """Dados do pedido para exportar via RPA."""
    order_id: UUID
    order_number: int
    customer_firebird_id: int
    customer_name: str
    total_amount: Decimal
    payment_method: Optional[str]
    items: List[Dict[str, Any]]  # [{product_code, quantity, unit_price}]
    notes: Optional[str] = None


class GasmasterRPA:
    """
    Robô RPA para automação do Gasmaster.

    Simula interação humana com a interface do Gasmaster para
    lançar vendas quando não há acesso de escrita ao banco.
    """

    def __init__(self, config: Optional[GasmasterConfig] = None):
        self.config = config or GasmasterConfig()
        self._app = None
        self._window = None

    @property
    def is_available(self) -> bool:
        """Verifica se as bibliotecas de automação estão disponíveis."""
        return PYAUTOGUI_AVAILABLE or PYWINAUTO_AVAILABLE

    def _log_action(self, action: str, details: str = ""):
        """Loga ação do robô."""
        logger.info(f"[RPA] {action}: {details}")

    # ==================== Conexão com Gasmaster ====================

    def find_gasmaster_window(self) -> bool:
        """
        Encontra a janela do Gasmaster.

        Returns:
            True se encontrou, False caso contrário
        """
        if not PYWINAUTO_AVAILABLE:
            self._log_action("ERRO", "pywinauto não disponível")
            return False

        try:
            # Tentar encontrar por título da janela
            desktop = Desktop(backend="uia")
            windows = desktop.windows()

            for win in windows:
                title = win.window_text()
                if self.config.window_title.lower() in title.lower():
                    self._app = Application(backend="uia").connect(handle=win.handle)
                    self._window = win
                    self._log_action("ENCONTRADO", f"Janela: {title}")
                    return True

            self._log_action("NAO_ENCONTRADO", f"Janela '{self.config.window_title}' não encontrada")
            return False

        except Exception as e:
            self._log_action("ERRO", f"Erro ao buscar janela: {e}")
            return False

    def is_gasmaster_open(self) -> bool:
        """Verifica se o Gasmaster está aberto."""
        return self.find_gasmaster_window()

    def focus_gasmaster(self) -> bool:
        """Traz a janela do Gasmaster para frente."""
        if not self._window:
            if not self.find_gasmaster_window():
                return False

        try:
            self._window.set_focus()
            time.sleep(0.5)
            return True
        except Exception as e:
            self._log_action("ERRO", f"Erro ao focar janela: {e}")
            return False

    # ==================== Ações Básicas ====================

    def click(self, x: int, y: int, clicks: int = 1):
        """Clica em uma posição da tela."""
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("pyautogui não disponível")

        self._log_action("CLICK", f"x={x}, y={y}, clicks={clicks}")
        pyautogui.click(x, y, clicks=clicks)
        time.sleep(self.config.action_delay)

    def click_control(self, control_name: str):
        """Clica em um controle da configuração."""
        coords = self.config.screen_vendas.get(control_name)
        if not coords:
            raise ValueError(f"Controle '{control_name}' não configurado")

        self.click(coords["x"], coords["y"])

    def type_text(self, text: str, clear_first: bool = True):
        """Digita texto no campo atual."""
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("pyautogui não disponível")

        if clear_first:
            # Seleciona tudo e apaga
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)

        self._log_action("TYPE", f"'{text[:20]}...' " if len(text) > 20 else f"'{text}'")
        pyautogui.typewrite(str(text), interval=self.config.typing_delay)
        time.sleep(self.config.action_delay)

    def type_text_unicode(self, text: str, clear_first: bool = True):
        """Digita texto com suporte a caracteres especiais."""
        if not PYWINAUTO_AVAILABLE:
            # Fallback para pyautogui
            self.type_text(text, clear_first)
            return

        if clear_first:
            send_keys("^a")  # Ctrl+A
            time.sleep(0.1)

        self._log_action("TYPE_UNICODE", f"'{text[:20]}...' " if len(text) > 20 else f"'{text}'")
        send_keys(text, with_spaces=True)
        time.sleep(self.config.action_delay)

    def press_key(self, key: str):
        """Pressiona uma tecla."""
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("pyautogui não disponível")

        self._log_action("KEY", key)
        pyautogui.press(key)
        time.sleep(self.config.action_delay)

    def press_tab(self, times: int = 1):
        """Pressiona TAB para navegar entre campos."""
        for _ in range(times):
            self.press_key("tab")

    def press_enter(self):
        """Pressiona ENTER."""
        self.press_key("enter")

    def press_escape(self):
        """Pressiona ESC."""
        self.press_key("escape")

    def hotkey(self, *keys):
        """Pressiona combinação de teclas."""
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("pyautogui não disponível")

        self._log_action("HOTKEY", "+".join(keys))
        pyautogui.hotkey(*keys)
        time.sleep(self.config.action_delay)

    # ==================== Screenshot para Debug ====================

    def take_screenshot(self, filename: str = None) -> str:
        """Tira screenshot da tela atual."""
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("pyautogui não disponível")

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rpa_screenshot_{timestamp}.png"

        screenshot_dir = Path("rpa_screenshots")
        screenshot_dir.mkdir(exist_ok=True)

        filepath = screenshot_dir / filename
        screenshot = pyautogui.screenshot()
        screenshot.save(str(filepath))

        self._log_action("SCREENSHOT", str(filepath))
        return str(filepath)

    # ==================== Fluxo de Venda ====================

    def navigate_to_sales_screen(self) -> bool:
        """
        Navega até a tela de lançamento de vendas.

        IMPORTANTE: Ajustar conforme layout do seu Gasmaster!
        """
        try:
            self._log_action("NAVEGANDO", "Tela de vendas")

            # Exemplo de navegação (AJUSTAR):
            # 1. Clicar no menu Vendas
            self.click_control("menu_vendas")
            time.sleep(0.5)

            # 2. Clicar em Nova Venda
            self.click_control("btn_nova_venda")
            time.sleep(1)

            return True

        except Exception as e:
            self._log_action("ERRO", f"Erro ao navegar: {e}")
            return False

    def fill_customer(self, customer_firebird_id: int) -> bool:
        """
        Preenche o campo de cliente.

        Args:
            customer_firebird_id: ID do cliente no Firebird
        """
        try:
            self._log_action("CLIENTE", f"ID={customer_firebird_id}")

            # Clicar no campo cliente
            self.click_control("campo_cliente")

            # Digitar código do cliente
            self.type_text(str(customer_firebird_id))

            # Pressionar TAB ou ENTER para confirmar
            self.press_tab()
            time.sleep(0.5)  # Aguardar busca do cliente

            return True

        except Exception as e:
            self._log_action("ERRO", f"Erro ao preencher cliente: {e}")
            return False

    def add_item(self, product_code: str, quantity: int, unit_price: Decimal) -> bool:
        """
        Adiciona um item à venda.

        Args:
            product_code: Código do produto (ex: P13)
            quantity: Quantidade
            unit_price: Preço unitário
        """
        try:
            self._log_action("ITEM", f"{product_code} x {quantity} @ R${unit_price}")

            # Campo produto
            self.click_control("campo_produto")
            self.type_text(product_code)
            self.press_tab()
            time.sleep(0.3)

            # Campo quantidade
            self.click_control("campo_quantidade")
            self.type_text(str(quantity))
            self.press_tab()

            # Campo preço (se editável)
            # self.click_control("campo_preco")
            # self.type_text(str(unit_price).replace(".", ","))
            # self.press_tab()

            # Adicionar item
            self.click_control("btn_adicionar_item")
            time.sleep(0.5)

            return True

        except Exception as e:
            self._log_action("ERRO", f"Erro ao adicionar item: {e}")
            return False

    def finalize_sale(self) -> bool:
        """Finaliza a venda."""
        try:
            self._log_action("FINALIZANDO", "Venda")

            # Clicar em Finalizar
            self.click_control("btn_finalizar")
            time.sleep(0.5)

            # Confirmar (se houver popup)
            self.click_control("btn_confirmar")
            time.sleep(1)

            return True

        except Exception as e:
            self._log_action("ERRO", f"Erro ao finalizar: {e}")
            return False

    # ==================== Exportação Completa ====================

    def export_order(self, order: OrderToExport) -> RPAStatus:
        """
        Exporta um pedido completo para o Gasmaster.

        Args:
            order: Dados do pedido

        Returns:
            Status da exportação
        """
        self._log_action("INICIANDO", f"Pedido #{order.order_number}")

        # 1. Verificar se Gasmaster está aberto
        if not self.is_gasmaster_open():
            self._log_action("ERRO", "Gasmaster não está aberto")
            return RPAStatus.GASMASTER_NOT_FOUND

        # 2. Focar na janela
        if not self.focus_gasmaster():
            return RPAStatus.FAILED

        try:
            # 3. Navegar para tela de vendas
            if not self.navigate_to_sales_screen():
                return RPAStatus.SCREEN_NOT_FOUND

            # 4. Preencher cliente
            if not self.fill_customer(order.customer_firebird_id):
                return RPAStatus.FAILED

            # 5. Adicionar itens
            for item in order.items:
                if not self.add_item(
                    product_code=item["product_code"],
                    quantity=item["quantity"],
                    unit_price=Decimal(str(item["unit_price"])),
                ):
                    return RPAStatus.FAILED

            # 6. Finalizar venda
            if not self.finalize_sale():
                return RPAStatus.FAILED

            self._log_action("SUCESSO", f"Pedido #{order.order_number} exportado")
            return RPAStatus.SUCCESS

        except Exception as e:
            self._log_action("ERRO", f"Exceção: {e}")
            self.take_screenshot(f"error_order_{order.order_number}.png")
            return RPAStatus.FAILED

    def export_orders_batch(self, orders: List[OrderToExport]) -> Dict[str, Any]:
        """
        Exporta múltiplos pedidos.

        Args:
            orders: Lista de pedidos

        Returns:
            Resumo da exportação
        """
        results = {
            "total": len(orders),
            "success": 0,
            "failed": 0,
            "details": []
        }

        for order in orders:
            status = self.export_order(order)

            result = {
                "order_number": order.order_number,
                "status": status.value,
            }
            results["details"].append(result)

            if status == RPAStatus.SUCCESS:
                results["success"] += 1
            else:
                results["failed"] += 1

            # Pausa entre pedidos
            time.sleep(1)

        return results


# ==================== Instância Global ====================

gasmaster_rpa = GasmasterRPA()


# ==================== Funções de Conveniência ====================

def check_rpa_available() -> Dict[str, Any]:
    """Verifica disponibilidade do RPA."""
    return {
        "available": gasmaster_rpa.is_available,
        "pyautogui": PYAUTOGUI_AVAILABLE,
        "pywinauto": PYWINAUTO_AVAILABLE,
        "gasmaster_open": gasmaster_rpa.is_gasmaster_open() if gasmaster_rpa.is_available else False,
    }


def export_order_via_rpa(order: OrderToExport) -> RPAStatus:
    """Exporta pedido via RPA."""
    return gasmaster_rpa.export_order(order)


# ==================== Calibração ====================

def calibrate_screen_positions():
    """
    Utilitário para descobrir posições dos controles na tela.

    Uso: Execute este script e mova o mouse para cada controle.
    As coordenadas serão exibidas em tempo real.
    """
    if not PYAUTOGUI_AVAILABLE:
        print("pyautogui não disponível!")
        return

    print("=" * 50)
    print("CALIBRAÇÃO DE POSIÇÕES DO GASMASTER")
    print("=" * 50)
    print("Mova o mouse para os controles desejados.")
    print("As coordenadas serão exibidas em tempo real.")
    print("Pressione Ctrl+C para sair.")
    print("=" * 50)

    try:
        while True:
            x, y = pyautogui.position()
            print(f"\rPosição: x={x:4}, y={y:4}", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nCalibração encerrada.")


if __name__ == "__main__":
    # Executar calibração se rodar diretamente
    calibrate_screen_positions()
