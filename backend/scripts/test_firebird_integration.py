#!/usr/bin/env python3
"""
Script de Teste e Análise da Integração Firebird

Testa:
1. Importação de dados do Firebird (produtos, clientes, estoque)
2. Exportação de pedidos para Firebird
3. Identifica o que falta para integração 100%
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone

# Adicionar backend ao path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.config import settings
from app.integrations.firebird import firebird_client
from app.services.firebird_export_service import export_order_to_firebird, FirebirdExportError
from app.database import AsyncSessionLocal
from app.models.order import Order, OrderStatus
from app.models.customer import Customer
from app.models.product import Product
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


async def test_firebird_connection():
    """Testa conexão com Firebird."""
    print_header("1. TESTE DE CONEXÃO FIREBIRD")
    
    if not firebird_client.is_available:
        print_error("Firebird não está disponível")
        print_info(f"Configurações:")
        print_info(f"  - Host: {settings.firebird_host}")
        print_info(f"  - Database: {settings.firebird_database}")
        print_info(f"  - User: {settings.firebird_user}")
        print_info(f"  - Enabled: {settings.firebird_enabled}")
        return False
    
    print_success("Firebird está disponível")
    
    try:
        # Testar conexão
        with firebird_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM RDB$DATABASE")
            cursor.fetchone()
            cursor.close()
        print_success("Conexão com Firebird estabelecida com sucesso")
        return True
    except Exception as e:
        print_error(f"Erro ao conectar: {e}")
        return False


async def test_import_products():
    """Testa importação de produtos do Firebird."""
    print_header("2. TESTE DE IMPORTAÇÃO - PRODUTOS")
    
    try:
        products = firebird_client.get_products(active_only=True)
        print_success(f"Produtos encontrados: {len(products)}")
        
        if products:
            # Mostrar alguns exemplos
            print_info("Exemplos de produtos:")
            for i, prod in enumerate(products[:5], 1):
                print(f"  {i}. {prod.get('code', 'N/A')} - {prod.get('name', 'N/A')} - R$ {prod.get('price', 0)}")
            
            # Testar busca por código
            if products:
                test_code = products[0].get('code', '')
                if test_code:
                    product = firebird_client.get_product_by_code(test_code)
                    if product:
                        print_success(f"Busca por código '{test_code}': OK")
                        print_info(f"  ID Firebird: {product.get('firebird_id')}")
                        print_info(f"  Nome: {product.get('name')}")
                        print_info(f"  Preço: R$ {product.get('price')}")
                    else:
                        print_warning(f"Busca por código '{test_code}': Não encontrado")
        else:
            print_warning("Nenhum produto encontrado no Firebird")
        
        return True
    except Exception as e:
        print_error(f"Erro ao importar produtos: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_import_customers():
    """Testa importação de clientes do Firebird."""
    print_header("3. TESTE DE IMPORTAÇÃO - CLIENTES")
    
    try:
        # Testar busca por telefone
        test_phones = ["4133460102", "41999999999", "41987654321"]
        found_any = False
        
        for phone in test_phones:
            customer = firebird_client.get_customer_by_phone(phone)
            if customer:
                found_any = True
                print_success(f"Cliente encontrado pelo telefone '{phone}':")
                print_info(f"  ID Firebird: {customer.get('firebird_id')}")
                print_info(f"  Nome: {customer.get('name')}")
                print_info(f"  CPF/CNPJ: {customer.get('cpf') or customer.get('cnpj') or 'N/A'}")
                print_info(f"  Telefone: {customer.get('phone')}")
                break
        
        if not found_any:
            print_warning("Nenhum cliente encontrado nos telefones de teste")
            print_info("Isso pode ser normal se não houver clientes cadastrados com esses telefones")
        
        return True
    except Exception as e:
        print_error(f"Erro ao importar clientes: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_import_stock():
    """Testa importação de estoque do Firebird."""
    print_header("4. TESTE DE IMPORTAÇÃO - ESTOQUE")
    
    try:
        stock = firebird_client.get_stock_levels(
            estlocal_id=1,
            esttipo_id=1,
            year=datetime.now().year,
            month=datetime.now().month
        )
        
        print_success(f"Itens de estoque encontrados: {len(stock)}")
        
        if stock:
            print_info("Exemplos de estoque:")
            for i, item in enumerate(stock[:5], 1):
                print(f"  {i}. {item.get('product_code', 'N/A')} - Qtd: {item.get('quantity', 0)}")
        else:
            print_warning("Nenhum item de estoque encontrado")
            print_info("Verifique se ESTLOCAL_ID=1 e ESTTIPO_ID=1 estão corretos")
        
        return True
    except Exception as e:
        print_error(f"Erro ao importar estoque: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_export_order():
    """Testa exportação de pedido para Firebird."""
    print_header("5. TESTE DE EXPORTAÇÃO - PEDIDOS")
    
    # Verificar configurações
    print_info("Configurações de exportação:")
    print_info(f"  - firebird_export_on_delivered: {settings.firebird_export_on_delivered}")
    print_info(f"  - firebird_trade_table: {settings.firebird_trade_table}")
    print_info(f"  - firebird_trade_item_table: {settings.firebird_trade_item_table}")
    print_info(f"  - firebird_trade_estab_id: {settings.firebird_trade_estab_id}")
    print_info(f"  - firebird_trade_tipomovest_id: {settings.firebird_trade_tipomovest_id}")
    print_info(f"  - firebird_trade_estlocal_id: {settings.firebird_trade_estlocal_id}")
    
    if not settings.firebird_export_on_delivered:
        print_warning("Exportação automática está DESABILITADA (firebird_export_on_delivered=False)")
        print_info("Para habilitar, configure FIREBIRD_EXPORT_ON_DELIVERED=true no .env")
    
    # Buscar pedidos entregues sem exportação
    async with AsyncSessionLocal() as session:
        # Buscar pedidos entregues sem exportação
        try:
            # Verificar se coluna existe
            from sqlalchemy import text
            check_result = await session.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'orders' AND column_name = 'firebird_trade_id'
                """)
            )
            has_firebird_column = check_result.scalar() is not None
            
            if not has_firebird_column:
                print_warning("Coluna firebird_trade_id não existe na tabela orders")
                print_info("Execute a migração: alembic upgrade head")
                return False
            
            result = await session.execute(
                select(Order.id)
                .where(
                    Order.status == OrderStatus.DELIVERED.value,
                    Order.firebird_trade_id.is_(None)
                )
                .order_by(Order.created_at.desc())
                .limit(5)
            )
            order_ids = [row[0] for row in result.all()]
            
            if not order_ids:
                print_warning("Nenhum pedido entregue sem exportação encontrado")
                print_info("Isso pode ser normal se todos os pedidos já foram exportados")
                return True
            
            print_info(f"Pedidos entregues sem exportação: {len(order_ids)}")
            
            # Buscar pedido completo com relacionamentos
            test_order_id = order_ids[0]
            result = await session.execute(
                select(Order)
                .options(
                    selectinload(Order.customer),
                    selectinload(Order.items),
                )
                .where(Order.id == test_order_id)
            )
            test_order = result.scalar_one_or_none()
            
            if not test_order:
                print_error("Erro ao buscar pedido completo")
                return False
        except Exception as e:
            print_error(f"Erro ao buscar pedidos: {e}")
            print_info("Pode ser que a tabela orders não tenha todas as colunas esperadas")
            return False
        print_info(f"\nTestando exportação do pedido #{test_order.order_number} (ID: {test_order.id})")
        print_info(f"  Status: {test_order.status}")
        print_info(f"  Total: R$ {test_order.total_amount}")
        print_info(f"  Cliente: {test_order.customer.phone if test_order.customer else 'N/A'}")
        print_info(f"  Itens: {len(test_order.items)}")
        
        # Verificar se cliente tem firebird_id
        if test_order.customer:
            if not test_order.customer.firebird_id:
                print_warning("Cliente não possui firebird_id")
                print_info("Tentando buscar no Firebird pelo telefone...")
                fb_customer = firebird_client.get_customer_by_phone(test_order.customer.phone)
                if fb_customer:
                    print_success(f"Cliente encontrado no Firebird: ID={fb_customer.get('firebird_id')}")
                    # Atualizar cliente
                    test_order.customer.firebird_id = fb_customer.get('firebird_id')
                    await session.commit()
                else:
                    print_error("Cliente não encontrado no Firebird")
                    print_warning("Exportação não será possível sem firebird_id do cliente")
                    return False
        
        # Verificar produtos
        missing_products = []
        for item in test_order.items:
            if not item.product_code:
                missing_products.append(f"Item sem código: {item.id}")
                continue
            
            product = firebird_client.get_product_by_code(item.product_code)
            if not product:
                missing_products.append(f"Produto não encontrado: {item.product_code}")
        
        if missing_products:
            print_error("Produtos não encontrados no Firebird:")
            for msg in missing_products:
                print_error(f"  - {msg}")
            print_warning("Exportação não será possível sem produtos válidos")
            return False
        else:
            print_success("Todos os produtos foram encontrados no Firebird")
        
        # Tentar exportar (apenas se tudo estiver OK)
        try:
            print_info("\nTentando exportar pedido...")
            trade_id = await export_order_to_firebird(test_order.id)
            print_success(f"Pedido exportado com sucesso! TRADE.ID = {trade_id}")
            
            # Verificar atualização
            await session.refresh(test_order)
            if test_order.firebird_trade_id:
                print_success(f"Pedido atualizado: firebird_trade_id = {test_order.firebird_trade_id}")
                print_success(f"Status: {test_order.firebird_export_status}")
            else:
                print_warning("Pedido não foi atualizado com firebird_trade_id")
            
            return True
        except FirebirdExportError as e:
            print_error(f"Erro na exportação: {e}")
            await session.refresh(test_order)
            if test_order.firebird_export_error:
                print_error(f"Erro salvo: {test_order.firebird_export_error}")
            return False
        except Exception as e:
            print_error(f"Erro inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False


async def analyze_missing_features():
    """Analisa o que falta para integração 100%."""
    print_header("6. ANÁLISE - O QUE FALTA PARA INTEGRAÇÃO 100%")
    
    missing = []
    
    # 1. Configuração
    if not settings.firebird_export_on_delivered:
        missing.append({
            "item": "Exportação automática desabilitada",
            "status": "config",
            "action": "Configurar FIREBIRD_EXPORT_ON_DELIVERED=true no .env"
        })
    
    if not settings.firebird_trade_estab_id:
        missing.append({
            "item": "ESTAB_ID não configurado",
            "status": "config",
            "action": "Configurar FIREBIRD_TRADE_ESTAB_ID no .env (ID do estabelecimento)"
        })
    
    if not settings.firebird_trade_tipomovest_id:
        missing.append({
            "item": "TIPOMOVEST_ID não configurado",
            "status": "config",
            "action": "Configurar FIREBIRD_TRADE_TIPOMOVEST_ID no .env (ID do tipo de movimento)"
        })
    
    # 2. Sincronização de dados
    async with AsyncSessionLocal() as session:
        # Verificar se há produtos sem código Firebird
        try:
            # Product pode ter firebird_code ou firebird_id
            from sqlalchemy import inspect
            product_cols = [c.name for c in inspect(Product).columns]
            
            if 'firebird_code' in product_cols:
                result = await session.execute(
                    select(Product).where(Product.firebird_code.is_(None)).limit(1)
                )
            elif 'firebird_id' in product_cols:
                result = await session.execute(
                    select(Product).where(Product.firebird_id.is_(None)).limit(1)
                )
            else:
                result = None
            
            if result:
                products_without_fb = result.scalars().first()
                if products_without_fb:
                    missing.append({
                        "item": "Produtos sem código Firebird",
                        "status": "sync",
                        "action": "Executar sincronização de produtos do Firebird"
                    })
        except Exception as e:
            print_warning(f"Erro ao verificar produtos: {e}")
        
        # Verificar se há clientes sem firebird_id
        try:
            result = await session.execute(
                select(Customer).where(Customer.firebird_id.is_(None)).limit(1)
            )
            customers_without_fb = result.scalars().first()
            if customers_without_fb:
                missing.append({
                    "item": "Clientes sem firebird_id",
                    "status": "sync",
                    "action": "Executar sincronização de clientes do Firebird ou buscar automaticamente"
                })
        except Exception as e:
            print_warning(f"Erro ao verificar clientes: {e}")
    
    # 3. Pedidos pendentes
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import text
            # Verificar se coluna existe
            check_result = await session.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'orders' AND column_name = 'firebird_trade_id'
                """)
            )
            has_firebird_column = check_result.scalar() is not None
            
            if has_firebird_column:
                result = await session.execute(
                    select(Order.id)
                    .where(
                        Order.status == OrderStatus.DELIVERED.value,
                        Order.firebird_trade_id.is_(None)
                    )
                )
                pending_order_ids = [row[0] for row in result.all()]
                if pending_order_ids:
                    missing.append({
                        "item": f"{len(pending_order_ids)} pedidos entregues sem exportação",
                        "status": "export",
                        "action": "Exportar pedidos pendentes manualmente ou habilitar exportação automática"
                    })
            else:
                missing.append({
                    "item": "Migração de exportação Firebird não aplicada",
                    "status": "config",
                    "action": "Execute: alembic upgrade head (migração 20260124_add_firebird_export_fields)"
                })
        except Exception as e:
            print_warning(f"Erro ao verificar pedidos pendentes: {e}")
    
    # 4. Campos opcionais do Firebird
    missing.append({
        "item": "Campos opcionais do TRADE (DOCUMENTO, SERIE, etc.)",
        "status": "enhancement",
        "action": "Verificar se campos adicionais são necessários para NF-e e relatórios fiscais"
    })
    
    # Exibir resultados
    if not missing:
        print_success("Nada identificado como faltando! Integração parece completa.")
    else:
        print_warning(f"Encontrados {len(missing)} itens pendentes:")
        print()
        
        for i, item in enumerate(missing, 1):
            status_color = {
                "config": Colors.YELLOW,
                "sync": Colors.BLUE,
                "export": Colors.RED,
                "enhancement": Colors.BLUE
            }.get(item["status"], Colors.RESET)
            
            print(f"{i}. {status_color}{item['item']}{Colors.RESET}")
            print(f"   Ação: {item['action']}")
            print()


async def generate_report():
    """Gera relatório final."""
    print_header("7. RELATÓRIO FINAL")
    
    async with AsyncSessionLocal() as session:
        # Estatísticas de pedidos
        result = await session.execute(
            select(Order)
            .where(Order.status == OrderStatus.DELIVERED.value)
        )
        delivered_orders = result.scalars().all()
        
        exported = sum(1 for o in delivered_orders if o.firebird_trade_id)
        not_exported = len(delivered_orders) - exported
        
        print_info("Estatísticas de Pedidos:")
        print(f"  Total entregues: {len(delivered_orders)}")
        print(f"  Exportados: {exported}")
        print(f"  Não exportados: {not_exported}")
        
        if not_exported > 0:
            print_warning(f"{not_exported} pedidos precisam ser exportados")
        
        # Estatísticas de clientes
        result = await session.execute(select(Customer))
        customers = result.scalars().all()
        customers_with_fb = sum(1 for c in customers if c.firebird_id)
        
        print_info("\nEstatísticas de Clientes:")
        print(f"  Total: {len(customers)}")
        print(f"  Com firebird_id: {customers_with_fb}")
        print(f"  Sem firebird_id: {len(customers) - customers_with_fb}")
        
        # Estatísticas de produtos
        result = await session.execute(select(Product))
        products = result.scalars().all()
        products_with_fb = sum(1 for p in products if p.firebird_id)
        
        print_info("\nEstatísticas de Produtos:")
        print(f"  Total: {len(products)}")
        print(f"  Com firebird_id: {products_with_fb}")
        print(f"  Sem firebird_id: {len(products) - products_with_fb}")


async def main():
    """Função principal."""
    print_header("ANÁLISE COMPLETA DA INTEGRAÇÃO FIREBIRD")
    
    results = {}
    
    # Testes
    results["connection"] = await test_firebird_connection()
    if not results["connection"]:
        print_error("\nNão é possível continuar sem conexão com Firebird")
        return
    
    results["products"] = await test_import_products()
    results["customers"] = await test_import_customers()
    results["stock"] = await test_import_stock()
    results["export"] = await test_export_order()
    
    # Análise
    await analyze_missing_features()
    await generate_report()
    
    # Resumo final
    print_header("RESUMO DOS TESTES")
    
    for test_name, passed in results.items():
        if passed:
            print_success(f"{test_name}: OK")
        else:
            print_error(f"{test_name}: FALHOU")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
