from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: str
    email: str
    full_name: str
    role: str  # Client, Provider, Admin


# Заглушки токенів згідно з рішенню D-06
MOCK_TOKENS = {
    "mock-client-token": CurrentUser(
        id="11111111-1111-1111-1111-111111111111",
        email="client@ukma.edu.ua",
        full_name="Іван Балабанов",
        role="Client",
    ),
    "mock-provider-token": CurrentUser(
        id="22222222-2222-2222-2222-222222222222",
        email="provider@ukma.edu.ua",
        full_name="Петро Відповідальний",
        role="Provider",
    ),
    "mock-admin-token": CurrentUser(
        id="33333333-3333-3333-3333-333333333333",
        email="admin@ukma.edu.ua",
        full_name="Олена Адмін",
        role="Admin",
    ),
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
) -> CurrentUser:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не надано заголовок авторизації або токен відсутній",
        )
    
    token = credentials.credentials
    if token not in MOCK_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний або застарілий токен авторизації",
        )
        
    return MOCK_TOKENS[token]

    # Використання ШІ: При написанні коду було використано допомогу ШІ Gemini. 
    # Код вичитано, відредаговано та затверджено учасниками команди