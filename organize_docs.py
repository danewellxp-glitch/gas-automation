#!/usr/bin/env python3
"""
Script de Organização Automática de Documentos
Organiza arquivos .md e .txt em pastas por tipo automaticamente.
"""

import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Configuração
PROJECT_ROOT = Path(__file__).parent
DOCS_ROOT = PROJECT_ROOT / "docs"

# Mapeamento de palavras-chave para categorias
# Ordem importa: categorias mais específicas primeiro
CATEGORY_KEYWORDS = {
    "resumos": [
        "resumo", "summary", "sumario", "conclusao", "final", "executivo"
    ],
    "relatorios": [
        "relatorio", "report", "varredura", "auditoria", "diagnostico",
        "estatisticas", "analise"
    ],
    "checklists": [
        "checklist", "lista", "verificacao"
    ],
    "planos": [
        "plano", "planejamento", "roadmap", "sprint", "fase"
    ],
    "guias": [
        "guia", "guide", "instrucoes", "tutorial", "como", "quick"
    ],
    "correcoes": [
        "correcao", "fix", "solucao", "problema", "erro", "bug"
    ],
    "migracoes": [
        "migracao", "migration", "conversao", "adaptacao"
    ],
    "arquitetura": [
        "arquitetura", "arquivo", "estrutura", "schema", "mapa", "diagrama"
    ],
    "testes": [
        "teste", "test", "debug"
    ],
    "scripts": [
        "script", "create", "generate", "sync"
    ],
    "configuracao": [
        "config", "setup", "deploy", "docker"
    ],
    "outros": []  # Fallback para arquivos não classificados
}

# Arquivos que devem permanecer na raiz
KEEP_IN_ROOT = {
    "README.md",
    ".gitignore",
    ".env.example",
    "docker-compose.yml"
}

# Pastas que devem ser ignoradas
IGNORE_DIRS = {
    "docs", "backend", "frontend", "grafana", "prometheus", 
    "vamos usar", ".git", "node_modules", "__pycache__", 
    "venv", ".venv", "env", ".env"
}


def normalize_filename(filename: str) -> str:
    """Normaliza o nome do arquivo para análise."""
    return filename.lower().replace("_", " ").replace("-", " ")


def classify_file(filename: str) -> str:
    """
    Classifica um arquivo baseado em palavras-chave no nome.
    Retorna a categoria apropriada.
    """
    normalized = normalize_filename(filename)
    
    # Verifica cada categoria
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "outros":
            continue
        
        for keyword in keywords:
            if keyword in normalized:
                return category
    
    # Se não encontrou, verifica extensões especiais
    if filename.endswith(".sh"):
        return "scripts"
    
    return "outros"


def should_organize_file(filepath: Path) -> bool:
    """Verifica se o arquivo deve ser organizado."""
    # Não organizar arquivos na raiz que devem ficar lá
    if filepath.name in KEEP_IN_ROOT:
        return False
    
    # Não organizar arquivos em pastas ignoradas
    for part in filepath.parts:
        if part in IGNORE_DIRS:
            return False
    
    # Apenas arquivos de documentação na raiz ou em docs/
    if filepath.suffix not in [".md", ".txt", ".docx", ".mmd", ".html"]:
        return False
    
    # Não organizar se já está dentro de docs/
    if "docs" in filepath.parts:
        return False
    
    return True


def find_files_to_organize(root: Path) -> List[Path]:
    """Encontra todos os arquivos que precisam ser organizados."""
    files_to_organize = []
    
    # Busca apenas na raiz do projeto
    for item in root.iterdir():
        if item.is_file() and should_organize_file(item):
            files_to_organize.append(item)
    
    return files_to_organize


def create_category_dirs(docs_root: Path):
    """Cria as pastas de categorias se não existirem."""
    for category in CATEGORY_KEYWORDS.keys():
        category_dir = docs_root / category
        category_dir.mkdir(parents=True, exist_ok=True)


def files_are_identical(file1: Path, file2: Path) -> bool:
    """Compara dois arquivos para verificar se são idênticos."""
    try:
        if not file1.exists() or not file2.exists():
            return False
        if file1.stat().st_size != file2.stat().st_size:
            return False
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            return f1.read() == f2.read()
    except Exception:
        return False


def organize_file(filepath: Path, category: str, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Move um arquivo para a pasta apropriada.
    Retorna (sucesso, mensagem)
    """
    docs_root = DOCS_ROOT
    category_dir = docs_root / category
    target_path = category_dir / filepath.name
    
    # Se o arquivo já está no lugar certo, não faz nada
    if filepath.resolve() == target_path.resolve():
        return True, f"✓ {filepath.name} já está em docs/{category}/"
    
    # Se já existe um arquivo com o mesmo nome no destino
    if target_path.exists():
        # Verifica se são idênticos
        if files_are_identical(filepath, target_path):
            # Arquivos são idênticos, apenas remove o da raiz
            if not dry_run:
                try:
                    filepath.unlink()
                    return True, f"✓ Duplicata removida (arquivo já existe em docs/{category}/)"
                except Exception as e:
                    return False, f"✗ Erro ao remover duplicata: {e}"
            else:
                return True, f"[DRY RUN] Duplicata seria removida (arquivo já existe em docs/{category}/)"
        else:
            # Arquivos são diferentes, adiciona timestamp para evitar sobrescrever
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = filepath.stem
            suffix = filepath.suffix
            new_name = f"{stem}_{timestamp}{suffix}"
            target_path = category_dir / new_name
            message = f"⚠ Arquivo duplicado com conteúdo diferente, renomeado para {new_name}"
    else:
        message = f"✓ Movido para docs/{category}/"
    
    if not dry_run:
        try:
            # Garante que a pasta existe
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # Move o arquivo
            shutil.move(str(filepath), str(target_path))
            return True, message
        except Exception as e:
            return False, f"✗ Erro ao mover: {e}"
    else:
        return True, f"[DRY RUN] {message}"


def organize_documents(dry_run: bool = False, verbose: bool = True) -> Dict[str, int]:
    """
    Organiza todos os documentos encontrados.
    Retorna estatísticas da operação.
    """
    stats = {
        "total": 0,
        "organizados": 0,
        "erros": 0,
        "por_categoria": {}
    }
    
    # Cria estrutura de pastas
    if not dry_run:
        create_category_dirs(DOCS_ROOT)
    
    # Encontra arquivos para organizar
    files_to_organize = find_files_to_organize(PROJECT_ROOT)
    stats["total"] = len(files_to_organize)
    
    if verbose:
        print(f"\n📁 Encontrados {stats['total']} arquivos para organizar\n")
    
    # Organiza cada arquivo
    for filepath in files_to_organize:
        category = classify_file(filepath.name)
        
        if category not in stats["por_categoria"]:
            stats["por_categoria"][category] = 0
        
        success, message = organize_file(filepath, category, dry_run)
        
        if success:
            stats["organizados"] += 1
            stats["por_categoria"][category] += 1
            if verbose:
                print(f"{message} → {filepath.name}")
        else:
            stats["erros"] += 1
            if verbose:
                print(f"{message} → {filepath.name}")
    
    return stats


def print_summary(stats: Dict):
    """Imprime resumo da organização."""
    print("\n" + "="*60)
    print("📊 RESUMO DA ORGANIZAÇÃO")
    print("="*60)
    print(f"Total de arquivos: {stats['total']}")
    print(f"Organizados: {stats['organizados']}")
    print(f"Erros: {stats['erros']}")
    print("\nPor categoria:")
    for category, count in sorted(stats["por_categoria"].items()):
        if count > 0:
            print(f"  • {category}: {count}")
    print("="*60 + "\n")


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Organiza documentos .md e .txt em pastas por tipo"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria feito sem fazer alterações"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Não mostra mensagens detalhadas"
    )
    
    args = parser.parse_args()
    
    print("🚀 Iniciando organização de documentos...")
    print(f"📂 Projeto: {PROJECT_ROOT}")
    print(f"📁 Destino: {DOCS_ROOT}")
    
    if args.dry_run:
        print("\n⚠️  MODO DRY RUN - Nenhuma alteração será feita\n")
    
    stats = organize_documents(dry_run=args.dry_run, verbose=not args.quiet)
    print_summary(stats)
    
    if args.dry_run:
        print("💡 Execute sem --dry-run para aplicar as mudanças\n")
    else:
        print("✅ Organização concluída!\n")


if __name__ == "__main__":
    main()
