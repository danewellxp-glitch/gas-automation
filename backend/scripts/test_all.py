#!/usr/bin/env python
"""
Script de teste completo para todas as funcionalidades criadas.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

# Carregar .env
env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ[key.strip()] = value.strip()

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("=" * 70)
print("           TESTE COMPLETO - GAS AUTOMATION")
print("=" * 70)
print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

tests_passed = 0
tests_failed = 0


def test(name, func):
    global tests_passed, tests_failed
    print(f"\n{'-'*70}")
    print(f"TESTE: {name}")
    print("-" * 70)
    try:
        result = func()
        if result:
            print(f"[OK] PASSOU")
            tests_passed += 1
        else:
            print(f"[X] FALHOU")
            tests_failed += 1
    except Exception as e:
        print(f"[X] ERRO: {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1


# ============================================================
# TESTE 1: Servico de Exportacao de Arquivos
# ============================================================
def test_file_export_service():
    from app.services.file_export_service import (
        FileExportService,
        ExportFormat,
        ExportedOrder,
        ExportedOrderItem
    )

    orders = [
        ExportedOrder(
            order_id=uuid4(),
            order_number=1001,
            created_at=datetime.now(),
            delivered_at=datetime.now(),
            total_amount=Decimal('150.00'),
            payment_method='pix',
            tipo_operacao='troca',
            notes='Teste automatizado',
            customer_id=uuid4(),
            customer_name='Cliente Teste',
            customer_phone='41999999999',
            customer_document='12345678901',
            customer_firebird_id=123,
            delivery_street='Rua Teste',
            delivery_number='100',
            delivery_complement='Sala 1',
            delivery_bairro='Centro',
            delivery_city='Curitiba',
            delivery_cep='80000000',
            items=[
                ExportedOrderItem(
                    sequence=1,
                    product_code='P13',
                    product_name='Gas P13',
                    quantity=2,
                    unit_price=Decimal('75.00'),
                    subtotal=Decimal('150.00'),
                )
            ]
        )
    ]

    service = FileExportService(export_dir='./test_exports')

    # CSV
    csv = service.generate_csv(orders)
    print(f"  CSV gerado: {len(csv)} bytes")
    assert 'PEDIDO_NUM' in csv

    # XML
    xml = service.generate_xml(orders)
    print(f"  XML gerado: {len(xml)} bytes")
    assert '<?xml' in xml

    # TXT
    txt = service.generate_gasmaster_txt(orders)
    print(f"  TXT gerado: {len(txt)} bytes")
    assert 'H0000001001' in txt

    return True


# ============================================================
# TESTE 2: API de Exports
# ============================================================
def test_exports_api():
    from app.api.exports import router

    endpoints = []
    for route in router.routes:
        if hasattr(route, 'path'):
            methods = list(getattr(route, 'methods', ['GET']))
            endpoints.append(f"{methods[0]} /api/exports{route.path}")

    print(f"  Endpoints encontrados: {len(endpoints)}")
    for ep in endpoints:
        print(f"    {ep}")

    return len(endpoints) >= 5


# ============================================================
# TESTE 3: Cliente Firebird - Metodos
# ============================================================
def test_firebird_client_methods():
    from app.integrations.firebird import FirebirdClient

    client = FirebirdClient()

    methods = [
        'get_products', 'get_product_by_code',
        'get_customer_by_phone', 'get_customer_by_address',
        'get_drivers', 'get_sales_points', 'get_stock_levels',
        'get_routes', 'get_vehicles', 'test_connection',
        'get_all_tables', 'get_table_columns',
        'get_table_primary_key', 'get_table_foreign_keys',
        'get_full_schema', 'describe_table', 'search_tables',
        'execute_raw_query'
    ]

    missing = []
    for method in methods:
        if hasattr(client, method):
            print(f"  OK {method}")
        else:
            print(f"  FALTA {method}")
            missing.append(method)

    return len(missing) == 0


# ============================================================
# TESTE 4: Conexao Real com Firebird
# ============================================================
def test_firebird_connection():
    from app.integrations.firebird import firebird_client

    print(f"  Host: {firebird_client.host}")
    print(f"  Database: {firebird_client.database}")
    print(f"  Configurado: {firebird_client.is_configured}")
    print(f"  Disponivel: {firebird_client.is_available}")

    if not firebird_client.is_available:
        print("  Firebird nao disponivel, pulando teste de conexao")
        return True

    connected = firebird_client.test_connection()
    print(f"  Conexao: {'OK' if connected else 'FALHOU'}")

    if connected:
        tables = firebird_client.get_all_tables()
        print(f"  Tabelas encontradas: {len(tables)}")

        products = firebird_client.get_products()
        print(f"  Produtos encontrados: {len(products)}")

    return connected


# ============================================================
# TESTE 5: API Firebird Schema
# ============================================================
def test_firebird_api():
    from app.api.firebird_schema import router

    endpoints = []
    for route in router.routes:
        if hasattr(route, 'path'):
            methods = list(getattr(route, 'methods', ['GET']))
            endpoints.append(f"{methods[0]} /api/firebird{route.path}")

    print(f"  Endpoints encontrados: {len(endpoints)}")
    for ep in endpoints:
        print(f"    {ep}")

    return len(endpoints) >= 10


# ============================================================
# TESTE 6: Servico RPA
# ============================================================
def test_rpa_service():
    from app.services.rpa_gasmaster_service import (
        GasmasterRPA,
        GasmasterConfig,
        RPAStatus,
        check_rpa_available,
        PYAUTOGUI_AVAILABLE,
        PYWINAUTO_AVAILABLE,
    )

    print(f"  PyAutoGUI: {'OK' if PYAUTOGUI_AVAILABLE else 'NAO INSTALADO'}")
    print(f"  PyWinAuto: {'OK' if PYWINAUTO_AVAILABLE else 'NAO INSTALADO'}")

    rpa = GasmasterRPA()
    print(f"  RPA disponivel: {rpa.is_available}")

    config = rpa.config
    print(f"  Window title: {config.window_title}")
    print(f"  Controles configurados: {len(config.screen_vendas)}")

    status = check_rpa_available()
    print(f"  Status: {status}")

    return PYAUTOGUI_AVAILABLE and PYWINAUTO_AVAILABLE


# ============================================================
# TESTE 7: API RPA
# ============================================================
def test_rpa_api():
    from app.api.rpa import router

    endpoints = []
    for route in router.routes:
        if hasattr(route, 'path'):
            methods = list(getattr(route, 'methods', ['GET']))
            endpoints.append(f"{methods[0]} /api/rpa{route.path}")

    print(f"  Endpoints encontrados: {len(endpoints)}")
    for ep in endpoints:
        print(f"    {ep}")

    return len(endpoints) >= 8


# ============================================================
# TESTE 8: Screenshot RPA
# ============================================================
def test_rpa_screenshot():
    from app.services.rpa_gasmaster_service import gasmaster_rpa

    if not gasmaster_rpa.is_available:
        print("  RPA nao disponivel")
        return True

    filepath = gasmaster_rpa.take_screenshot("test_screenshot.png")
    print(f"  Screenshot salvo: {filepath}")

    exists = os.path.exists(filepath)
    print(f"  Arquivo existe: {exists}")

    if exists:
        os.remove(filepath)
        print(f"  Arquivo removido")

    return exists


# ============================================================
# TESTE 9: Posicao do Mouse
# ============================================================
def test_mouse_position():
    try:
        import pyautogui
        x, y = pyautogui.position()
        print(f"  Posicao do mouse: x={x}, y={y}")

        size = pyautogui.size()
        print(f"  Resolucao da tela: {size.width}x{size.height}")
        return True
    except ImportError:
        print("  pyautogui nao instalado")
        return False


# ============================================================
# TESTE 10: Modelo Order - Campos de Exportacao
# ============================================================
def test_order_model():
    from app.models.order import Order
    import inspect

    source = inspect.getsource(Order)

    fields = [
        'firebird_trade_id',
        'firebird_export_status',
        'firebird_exported_at',
        'file_export_status',
        'file_exported_at',
    ]

    found = []
    missing = []
    for field in fields:
        if field in source:
            print(f"  OK {field}")
            found.append(field)
        else:
            print(f"  FALTA {field}")
            missing.append(field)

    return len(missing) == 0


# ============================================================
# EXECUTAR TESTES
# ============================================================
if __name__ == "__main__":
    test("1. Servico de Exportacao de Arquivos", test_file_export_service)
    test("2. API de Exports", test_exports_api)
    test("3. Cliente Firebird - Metodos", test_firebird_client_methods)
    test("4. Conexao Real com Firebird", test_firebird_connection)
    test("5. API Firebird Schema", test_firebird_api)
    test("6. Servico RPA", test_rpa_service)
    test("7. API RPA", test_rpa_api)
    test("8. Screenshot RPA", test_rpa_screenshot)
    test("9. Posicao do Mouse", test_mouse_position)
    test("10. Modelo Order - Campos", test_order_model)

    # Resumo
    print("\n" + "=" * 70)
    print("                         RESUMO DOS TESTES")
    print("=" * 70)
    total = tests_passed + tests_failed
    print(f"""
  Passou: {tests_passed}
  Falhou: {tests_failed}
  Total:  {total}

  Taxa de sucesso: {tests_passed / total * 100:.1f}%
""")
    print("=" * 70)

    # Limpar
    import shutil
    if os.path.exists('./test_exports'):
        shutil.rmtree('./test_exports')
    if os.path.exists('./rpa_screenshots'):
        shutil.rmtree('./rpa_screenshots')
