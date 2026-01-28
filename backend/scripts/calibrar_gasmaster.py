#!/usr/bin/env python
"""
Script de Calibração do Gasmaster para RPA.

Este script ajuda a descobrir as coordenadas dos controles na tela
do Gasmaster para configurar o robô de automação.

Uso:
    python calibrar_gasmaster.py

Instruções:
    1. Abra o Gasmaster e deixe na tela desejada
    2. Execute este script
    3. Mova o mouse para cada controle
    4. Pressione ESPAÇO para salvar a posição
    5. As coordenadas serão salvas em um arquivo JSON

Requisitos:
    pip install pyautogui keyboard
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime

try:
    import pyautogui
except ImportError:
    print("ERRO: pyautogui não instalado!")
    print("Execute: pip install pyautogui")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    print("ERRO: keyboard não instalado!")
    print("Execute: pip install keyboard")
    sys.exit(1)


# Controles a serem calibrados
CONTROLES = [
    ("menu_vendas", "Menu Vendas (ou atalho para abrir vendas)"),
    ("btn_nova_venda", "Botão Nova Venda"),
    ("campo_cliente", "Campo Código do Cliente"),
    ("campo_produto", "Campo Código do Produto"),
    ("campo_quantidade", "Campo Quantidade"),
    ("campo_preco", "Campo Preço Unitário"),
    ("btn_adicionar_item", "Botão Adicionar Item"),
    ("btn_finalizar", "Botão Finalizar/Gravar Venda"),
    ("btn_confirmar", "Botão Confirmar (se houver popup)"),
]


def clear_screen():
    """Limpa a tela."""
    print("\033[H\033[J", end="")


def print_header():
    """Imprime cabeçalho."""
    clear_screen()
    print("=" * 60)
    print("       CALIBRAÇÃO DO GASMASTER PARA AUTOMAÇÃO RPA")
    print("=" * 60)
    print()


def get_mouse_position():
    """Retorna posição atual do mouse."""
    return pyautogui.position()


def save_positions(positions: dict, filename: str = "gasmaster_positions.json"):
    """Salva posições em arquivo JSON."""
    output_dir = Path(__file__).parent.parent / "config"
    output_dir.mkdir(exist_ok=True)

    filepath = output_dir / filename

    data = {
        "calibrated_at": datetime.now().isoformat(),
        "screen_size": pyautogui.size(),
        "positions": positions,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def calibrate_single_control(name: str, description: str) -> dict:
    """
    Calibra um único controle.

    Returns:
        Dicionário com x, y
    """
    print(f"\n{'='*60}")
    print(f"CONTROLE: {name}")
    print(f"Descrição: {description}")
    print("=" * 60)
    print()
    print("Instruções:")
    print("  1. Posicione o mouse sobre o controle")
    print("  2. Pressione ESPAÇO para capturar")
    print("  3. Pressione ESC para pular este controle")
    print()
    print("Posição atual do mouse:")

    captured = None

    while True:
        x, y = get_mouse_position()
        print(f"\r  X: {x:4}  Y: {y:4}    ", end="", flush=True)

        if keyboard.is_pressed("space"):
            captured = {"x": x, "y": y}
            print(f"\n\n✓ CAPTURADO: x={x}, y={y}")
            time.sleep(0.3)  # Debounce
            break

        if keyboard.is_pressed("escape"):
            print("\n\n⏭ PULADO")
            time.sleep(0.3)
            break

        time.sleep(0.05)

    return captured


def run_calibration():
    """Executa calibração completa."""
    print_header()

    print("PREPARAÇÃO:")
    print("-" * 60)
    print("1. Abra o Gasmaster")
    print("2. Faça login no sistema")
    print("3. Deixe visível a tela que será automatizada")
    print()
    print("Pressione ENTER quando estiver pronto...")
    input()

    positions = {}

    for name, description in CONTROLES:
        pos = calibrate_single_control(name, description)
        if pos:
            positions[name] = pos

        print("\nPressione ENTER para continuar...")
        input()

    # Mostrar resumo
    print_header()
    print("RESUMO DA CALIBRAÇÃO")
    print("=" * 60)
    print()

    for name, description in CONTROLES:
        pos = positions.get(name)
        if pos:
            print(f"  ✓ {name:25} x={pos['x']:4}, y={pos['y']:4}")
        else:
            print(f"  ✗ {name:25} (não calibrado)")

    print()

    if positions:
        filepath = save_positions(positions)
        print(f"Posições salvas em: {filepath}")
        print()

        # Gerar código Python
        print("=" * 60)
        print("CÓDIGO PARA CONFIGURAÇÃO:")
        print("=" * 60)
        print()
        print("screen_vendas = {")
        for name, pos in positions.items():
            print(f'    "{name}": {{"x": {pos["x"]}, "y": {pos["y"]}}},')
        print("}")

    print()
    print("Calibração concluída!")


def monitor_mode():
    """Modo monitor - mostra posição do mouse em tempo real."""
    print_header()
    print("MODO MONITOR")
    print("=" * 60)
    print()
    print("Mostrando posição do mouse em tempo real.")
    print("Pressione Ctrl+C para sair.")
    print()

    try:
        while True:
            x, y = get_mouse_position()
            print(f"\rPosição: x={x:4}, y={y:4}    ", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n\nMonitor encerrado.")


def main():
    """Função principal."""
    print_header()
    print("Selecione o modo:")
    print()
    print("  1. Calibração completa (guiada)")
    print("  2. Modo monitor (mostrar posições)")
    print("  3. Sair")
    print()

    choice = input("Opção: ").strip()

    if choice == "1":
        run_calibration()
    elif choice == "2":
        monitor_mode()
    else:
        print("Saindo...")


if __name__ == "__main__":
    main()
