"""
Testes para integração com Asaas.
"""

import pytest

# Integração Asaas/Pix foi descontinuada.
pytest.skip("Asaas/Pix descontinuado: testes desativados", allow_module_level=True)


# ==================== Fixtures ====================

@pytest.fixture
def mock_asaas_customer():
    """Mock de cliente Asaas."""
    return {
        "id": "cus_000005113026",
        "name": "João Silva",
        "cpfCnpj": "12345678901",
        "email": "joao@email.com",
        "phone": "41999998888",
        "mobilePhone": "41999998888",
        "dateCreated": "2024-01-15",
    }


@pytest.fixture
def mock_asaas_pix_payment():
    """Mock de pagamento Pix."""
    return {
        "id": "pay_3hf9v8n4tq5j",
        "customer": "cus_000005113026",
        "billingType": "PIX",
        "value": 110.0,
        "netValue": 108.35,
        "status": "PENDING",
        "dueDate": "2024-01-16",
        "invoiceUrl": "https://www.asaas.com/i/3hf9v8n4tq5j",
        "externalReference": "order_123",
        "pix": {
            "encodedImage": "iVBORw0KGgoAAAANSUhEUgAAAQA...",
            "payload": "00020126580014br.gov.bcb.pix...",
            "expirationDate": "2024-01-16T23:59:59",
        },
    }


@pytest.fixture
def mock_asaas_card_payment():
    """Mock de pagamento com cartão."""
    return {
        "id": "pay_abc123def456",
        "customer": "cus_000005113026",
        "billingType": "CREDIT_CARD",
        "value": 220.0,
        "netValue": 214.5,
        "status": "CONFIRMED",
        "dueDate": "2024-01-15",
        "confirmedDate": "2024-01-15",
        "externalReference": "order_456",
    }


@pytest.fixture
def mock_asaas_boleto_payment():
    """Mock de pagamento com boleto."""
    return {
        "id": "pay_xyz789",
        "customer": "cus_000005113026",
        "billingType": "BOLETO",
        "value": 150.0,
        "status": "PENDING",
        "dueDate": "2024-01-20",
        "bankSlipUrl": "https://www.asaas.com/b/xyz789",
        "invoiceUrl": "https://www.asaas.com/i/xyz789",
        "externalReference": "order_789",
    }


# ==================== Testes do AsaasClient ====================

class TestAsaasClient:
    """Testes do cliente Asaas."""

    @pytest.mark.asyncio
    async def test_create_customer_success(self, mock_asaas_customer):
        """Testa criação de cliente com sucesso."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_asaas_customer

            result = await client.create_customer(
                name="João Silva",
                cpf_cnpj="123.456.789-01",
                email="joao@email.com",
                phone="41999998888",
            )

            assert result["id"] == "cus_000005113026"
            assert result["name"] == "João Silva"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_customer_invalid_cpf(self):
        """Testa erro ao criar cliente com CPF inválido."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = AsaasError(
                message="CPF/CNPJ inválido",
                status_code=400,
                errors=[{"code": "invalid_cpfCnpj", "description": "CPF/CNPJ inválido"}]
            )

            with pytest.raises(AsaasError) as exc_info:
                await client.create_customer(
                    name="Teste",
                    cpf_cnpj="invalid",
                )

            assert "inválido" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_customer_by_cpf(self, mock_asaas_customer):
        """Testa busca de cliente por CPF."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"data": [mock_asaas_customer], "hasMore": False}

            result = await client.find_customer_by_cpf_cnpj("12345678901")

            assert result is not None
            assert result["id"] == "cus_000005113026"

    @pytest.mark.asyncio
    async def test_find_customer_not_found(self):
        """Testa busca de cliente não encontrado."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"data": [], "hasMore": False}

            result = await client.find_customer_by_cpf_cnpj("99999999999")

            assert result is None

    @pytest.mark.asyncio
    async def test_create_pix_payment_success(self, mock_asaas_pix_payment):
        """Testa criação de pagamento Pix."""
        client = AsaasClient()

        # Mock para criar pagamento
        async def mock_request(method, endpoint, **kwargs):
            if endpoint == "/payments":
                return {k: v for k, v in mock_asaas_pix_payment.items() if k != "pix"}
            elif "pixQrCode" in endpoint:
                return mock_asaas_pix_payment["pix"]
            return {}

        with patch.object(client, '_request', side_effect=mock_request):
            result = await client.create_pix_payment(
                customer_id="cus_000005113026",
                value=Decimal("110.00"),
                description="Pedido #123",
                external_reference="order_123",
            )

            assert result["id"] == "pay_3hf9v8n4tq5j"
            assert result["billingType"] == "PIX"
            assert "pix" in result

    @pytest.mark.asyncio
    async def test_get_pix_qr_code(self, mock_asaas_pix_payment):
        """Testa obtenção de QR Code Pix."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_asaas_pix_payment["pix"]

            result = await client.get_pix_qr_code("pay_3hf9v8n4tq5j")

            assert "encodedImage" in result
            assert "payload" in result
            assert "expirationDate" in result

    @pytest.mark.asyncio
    async def test_create_credit_card_payment(self, mock_asaas_card_payment):
        """Testa criação de pagamento com cartão."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_asaas_card_payment

            result = await client.create_credit_card_payment(
                customer_id="cus_000005113026",
                value=Decimal("220.00"),
                description="Pedido #456",
                credit_card={
                    "holderName": "JOAO SILVA",
                    "number": "4111111111111111",
                    "expiryMonth": "12",
                    "expiryYear": "2025",
                    "ccv": "123",
                },
                credit_card_holder_info={
                    "name": "João Silva",
                    "email": "joao@email.com",
                    "cpfCnpj": "12345678901",
                    "postalCode": "80000000",
                    "addressNumber": "123",
                    "phone": "41999998888",
                },
                external_reference="order_456",
            )

            assert result["id"] == "pay_abc123def456"
            assert result["status"] == "CONFIRMED"

    @pytest.mark.asyncio
    async def test_create_boleto_payment(self, mock_asaas_boleto_payment):
        """Testa criação de pagamento com boleto."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_asaas_boleto_payment

            result = await client.create_boleto_payment(
                customer_id="cus_000005113026",
                value=Decimal("150.00"),
                description="Pedido #789",
                external_reference="order_789",
            )

            assert result["id"] == "pay_xyz789"
            assert result["billingType"] == "BOLETO"
            assert "bankSlipUrl" in result

    @pytest.mark.asyncio
    async def test_get_payment_status(self, mock_asaas_pix_payment):
        """Testa consulta de status de pagamento."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_asaas_pix_payment

            result = await client.get_payment_status("pay_3hf9v8n4tq5j")

            assert result == "PENDING"

    @pytest.mark.asyncio
    async def test_cancel_payment(self):
        """Testa cancelamento de pagamento."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"deleted": True}

            result = await client.cancel_payment("pay_3hf9v8n4tq5j")

            assert result["deleted"] is True

    @pytest.mark.asyncio
    async def test_refund_payment(self):
        """Testa estorno de pagamento."""
        client = AsaasClient()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "pay_3hf9v8n4tq5j", "status": "REFUND_REQUESTED"}

            result = await client.refund_payment("pay_3hf9v8n4tq5j")

            assert result["status"] == "REFUND_REQUESTED"


# ==================== Testes de Funções de Conveniência ====================

class TestAsaasConvenienceFunctions:
    """Testes das funções de conveniência."""

    @pytest.mark.asyncio
    async def test_create_pix_payment_function(self, mock_asaas_customer, mock_asaas_pix_payment):
        """Testa função de alto nível para criar Pix."""
        with patch.object(asaas_client, 'get_or_create_customer', new_callable=AsyncMock) as mock_customer:
            mock_customer.return_value = mock_asaas_customer

            async def mock_pix(*args, **kwargs):
                return mock_asaas_pix_payment

            with patch.object(asaas_client, 'create_pix_payment', side_effect=mock_pix):
                result = await create_pix_payment(
                    customer_name="João Silva",
                    customer_cpf_cnpj="12345678901",
                    value=Decimal("110.00"),
                    description="2x Gás P13",
                    order_id="order_123",
                )

                assert result["id"] == "pay_3hf9v8n4tq5j"

    @pytest.mark.asyncio
    async def test_check_payment_status_function(self, mock_asaas_pix_payment):
        """Testa função de verificação de status."""
        with patch.object(asaas_client, 'get_payment', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_asaas_pix_payment

            result = await check_payment_status("pay_3hf9v8n4tq5j")

            assert result["status"] == "PENDING"
            assert result["value"] == 110.0


# ==================== Testes do PaymentService ====================

class TestPaymentService:
    """Testes do serviço de pagamentos."""

    def test_map_asaas_status_pending(self):
        """Testa mapeamento de status PENDING."""
        service = PaymentService()
        result = service._map_asaas_status("PENDING")
        assert result == PaymentStatus.PENDING.value

    def test_map_asaas_status_confirmed(self):
        """Testa mapeamento de status CONFIRMED."""
        service = PaymentService()
        result = service._map_asaas_status("CONFIRMED")
        assert result == PaymentStatus.CONFIRMED.value

    def test_map_asaas_status_received(self):
        """Testa mapeamento de status RECEIVED."""
        service = PaymentService()
        result = service._map_asaas_status("RECEIVED")
        assert result == PaymentStatus.RECEIVED.value

    def test_map_asaas_status_overdue(self):
        """Testa mapeamento de status OVERDUE."""
        service = PaymentService()
        result = service._map_asaas_status("OVERDUE")
        assert result == PaymentStatus.OVERDUE.value

    def test_map_asaas_status_refunded(self):
        """Testa mapeamento de status REFUNDED."""
        service = PaymentService()
        result = service._map_asaas_status("REFUNDED")
        assert result == PaymentStatus.REFUNDED.value

    def test_map_asaas_status_unknown(self):
        """Testa mapeamento de status desconhecido."""
        service = PaymentService()
        result = service._map_asaas_status("UNKNOWN_STATUS")
        assert result == PaymentStatus.PENDING.value

    def test_parse_datetime_valid(self):
        """Testa parse de datetime válido."""
        service = PaymentService()
        result = service._parse_datetime("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_datetime_with_z(self):
        """Testa parse de datetime com Z."""
        service = PaymentService()
        result = service._parse_datetime("2024-01-15T10:30:00Z")
        assert result is not None

    def test_parse_datetime_none(self):
        """Testa parse de datetime None."""
        service = PaymentService()
        result = service._parse_datetime(None)
        assert result is None

    def test_parse_date_valid(self):
        """Testa parse de date válido."""
        service = PaymentService()
        result = service._parse_date("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_none(self):
        """Testa parse de date None."""
        service = PaymentService()
        result = service._parse_date(None)
        assert result is None


# ==================== Testes de Webhook ====================

class TestWebhookHandlers:
    """Testes dos handlers de webhook."""

    @pytest.mark.asyncio
    async def test_asaas_webhook_payment_received(self, client):
        """Testa webhook de pagamento recebido."""
        payload = {
            "event": "PAYMENT_RECEIVED",
            "payment": {
                "id": "pay_test123",
                "status": "RECEIVED",
                "value": 110.0,
                "netValue": 108.35,
                "externalReference": "order_123",
            }
        }

        response = await client.post("/webhooks/asaas", json=payload)

        # Webhook deve retornar sucesso mesmo se não encontrar o pagamento
        assert response.status_code == 200
        assert response.json()["status"] == "processing"

    @pytest.mark.asyncio
    async def test_asaas_webhook_payment_overdue(self, client):
        """Testa webhook de pagamento vencido."""
        payload = {
            "event": "PAYMENT_OVERDUE",
            "payment": {
                "id": "pay_test456",
                "status": "OVERDUE",
                "externalReference": "order_456",
            }
        }

        response = await client.post("/webhooks/asaas", json=payload)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_asaas_webhook_no_payment_data(self, client):
        """Testa webhook sem dados de pagamento."""
        payload = {
            "event": "PAYMENT_RECEIVED",
        }

        response = await client.post("/webhooks/asaas", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"


# ==================== Testes de Integração (se API disponível) ====================

@pytest.mark.skip(reason="Requer API Asaas real - rodar manualmente")
class TestAsaasIntegration:
    """
    Testes de integração real com API Asaas.

    Rodar apenas em ambiente de desenvolvimento com credenciais válidas:
    pytest tests/test_integrations/test_asaas.py::TestAsaasIntegration -v --no-skip
    """

    @pytest.mark.asyncio
    async def test_real_create_customer(self):
        """Testa criação real de cliente no Asaas sandbox."""
        import uuid

        result = await asaas_client.create_customer(
            name=f"Teste {uuid.uuid4().hex[:8]}",
            cpf_cnpj="71946627054",  # CPF válido para teste
            email="teste@example.com",
            phone="41999999999",
        )

        assert "id" in result
        print(f"Cliente criado: {result['id']}")

    @pytest.mark.asyncio
    async def test_real_create_pix(self):
        """Testa criação real de Pix no Asaas sandbox."""
        # Primeiro criar cliente
        customer = await asaas_client.get_or_create_customer(
            name="Teste Pix",
            cpf_cnpj="71946627054",
        )

        # Criar pagamento Pix
        result = await asaas_client.create_pix_payment(
            customer_id=customer["id"],
            value=Decimal("10.00"),
            description="Teste Pix",
            external_reference="test_order_001",
        )

        assert "id" in result
        assert "pix" in result
        print(f"Pix criado: {result['id']}")
        print(f"QR Code disponível: {'encodedImage' in result['pix']}")
