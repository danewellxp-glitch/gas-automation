"""
Testes de carga para simular pico de pedidos.
Simula 9.000 pedidos/semana = ~1.300 pedidos/dia = ~54 pedidos/hora (pico ~150/hora)
"""

import asyncio
import time
import statistics
from typing import List
from dataclasses import dataclass
import httpx


@dataclass
class LoadTestResult:
    """Resultado do teste de carga."""
    total_requests: int
    successful: int
    failed: int
    duration_seconds: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    requests_per_second: float


class LoadTester:
    """Executor de testes de carga."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.response_times: List[float] = []
        self.errors: List[str] = []

    async def simulate_message(self, client: httpx.AsyncClient, phone: str, message: str) -> bool:
        """Simula envio de mensagem pelo bot."""
        start = time.time()
        try:
            response = await client.post(
                f"{self.base_url}/api/test/simulate-message",
                json={"phone": phone, "message": message},
                timeout=10.0
            )
            elapsed = (time.time() - start) * 1000
            self.response_times.append(elapsed)
            return response.status_code == 200
        except Exception as e:
            self.errors.append(str(e))
            return False

    async def simulate_order_flow(self, client: httpx.AsyncClient, user_id: int) -> bool:
        """Simula fluxo completo de pedido."""
        phone = f"5541{900000000 + user_id}"

        # Inicia conversa
        if not await self.simulate_message(client, phone, "oi"):
            return False

        # Seleciona produto
        if not await self.simulate_message(client, phone, "P13"):
            return False

        # Quantidade
        if not await self.simulate_message(client, phone, "2"):
            return False

        return True

    async def run_concurrent_requests(
        self,
        num_users: int,
        requests_per_user: int = 1
    ) -> LoadTestResult:
        """Executa requisições concorrentes."""
        self.response_times = []
        self.errors = []

        start_time = time.time()

        async with httpx.AsyncClient() as client:
            tasks = []
            for user_id in range(num_users):
                for _ in range(requests_per_user):
                    tasks.append(self.simulate_order_flow(client, user_id))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - start_time
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful

        if self.response_times:
            sorted_times = sorted(self.response_times)
            p95_idx = int(len(sorted_times) * 0.95)

            return LoadTestResult(
                total_requests=len(results),
                successful=successful,
                failed=failed,
                duration_seconds=duration,
                avg_response_time_ms=statistics.mean(self.response_times),
                min_response_time_ms=min(self.response_times),
                max_response_time_ms=max(self.response_times),
                p95_response_time_ms=sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1],
                requests_per_second=len(results) / duration
            )
        else:
            return LoadTestResult(
                total_requests=len(results),
                successful=0,
                failed=len(results),
                duration_seconds=duration,
                avg_response_time_ms=0,
                min_response_time_ms=0,
                max_response_time_ms=0,
                p95_response_time_ms=0,
                requests_per_second=0
            )


def print_result(result: LoadTestResult, test_name: str):
    """Imprime resultado formatado."""
    print(f"\n{'='*50}")
    print(f"  {test_name}")
    print(f"{'='*50}")
    print(f"  Total de requisições: {result.total_requests}")
    print(f"  Sucesso: {result.successful} ({result.successful/result.total_requests*100:.1f}%)")
    print(f"  Falhas: {result.failed}")
    print(f"  Duração: {result.duration_seconds:.2f}s")
    print(f"  Requisições/segundo: {result.requests_per_second:.1f}")
    print(f"  Tempo resposta (avg): {result.avg_response_time_ms:.1f}ms")
    print(f"  Tempo resposta (min): {result.min_response_time_ms:.1f}ms")
    print(f"  Tempo resposta (max): {result.max_response_time_ms:.1f}ms")
    print(f"  Tempo resposta (p95): {result.p95_response_time_ms:.1f}ms")
    print(f"{'='*50}\n")


async def run_load_tests():
    """Executa bateria de testes de carga."""
    tester = LoadTester()

    # Teste 1: 10 usuários simultâneos (carga leve)
    print("\n[1/3] Teste de carga leve: 10 usuários simultâneos...")
    result = await tester.run_concurrent_requests(num_users=10)
    print_result(result, "Carga Leve (10 usuários)")

    # Teste 2: 50 usuários simultâneos (carga média)
    print("[2/3] Teste de carga média: 50 usuários simultâneos...")
    result = await tester.run_concurrent_requests(num_users=50)
    print_result(result, "Carga Média (50 usuários)")

    # Teste 3: 100 usuários simultâneos (pico)
    print("[3/3] Teste de carga alta: 100 usuários simultâneos (simula pico)...")
    result = await tester.run_concurrent_requests(num_users=100)
    print_result(result, "Carga Alta/Pico (100 usuários)")

    # Avaliação
    if result.successful / result.total_requests >= 0.95 and result.p95_response_time_ms < 2000:
        print("✅ APROVADO: Sistema suporta carga de pico esperada")
        return True
    else:
        print("⚠️ ATENÇÃO: Performance abaixo do esperado sob carga")
        return False


if __name__ == "__main__":
    asyncio.run(run_load_tests())
