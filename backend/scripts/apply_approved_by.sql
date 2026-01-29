-- Migration para adicionar campo approved_by na tabela orders
-- Execute este script diretamente no PostgreSQL

-- Adicionar coluna approved_by se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'approved_by'
    ) THEN
        ALTER TABLE orders 
        ADD COLUMN approved_by INTEGER 
        REFERENCES users(id) ON DELETE SET NULL;
        
        RAISE NOTICE 'Coluna approved_by adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna approved_by já existe';
    END IF;
END $$;

-- Criar índice se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'orders' AND indexname = 'ix_orders_approved_by'
    ) THEN
        CREATE INDEX ix_orders_approved_by ON orders(approved_by);
        
        RAISE NOTICE 'Índice ix_orders_approved_by criado com sucesso';
    ELSE
        RAISE NOTICE 'Índice ix_orders_approved_by já existe';
    END IF;
END $$;
