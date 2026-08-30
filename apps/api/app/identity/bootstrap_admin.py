"""One-time operational command to promote an existing account to ADMIN.

Usage inside the running API container:
    python -m app.identity.bootstrap_admin admin@example.com

The account must first be created through the normal registration flow. Keeping the
bootstrap operation out of HTTP prevents a public endpoint from becoming a privilege
escalation path.
"""

import asyncio
import sys

from app.config import get_settings
from app.identity.models import Role
from app.identity.repository import PostgresIdentityRepository


async def promote(email: str) -> int:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        print("Informe um e-mail válido.", file=sys.stderr)
        return 2

    repository = PostgresIdentityRepository(get_settings())
    user = await repository.get_user_by_email(normalized)
    if user is None:
        print(
            "Conta não encontrada. Cadastre a conta pelo fluxo normal antes de promovê-la.",
            file=sys.stderr,
        )
        return 3
    if user.role is Role.ADMIN:
        print(f"{normalized} já é ADMIN.")
        return 0

    updated = await repository.update_user_role(user.id, Role.ADMIN)
    if updated is None:
        print("Não foi possível atualizar a conta.", file=sys.stderr)
        return 4

    print(f"{normalized} promovido a ADMIN. Sessões anteriores foram revogadas; faça login novamente.")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python -m app.identity.bootstrap_admin EMAIL", file=sys.stderr)
        return 2
    return asyncio.run(promote(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
