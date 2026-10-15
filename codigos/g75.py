from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Simulação de "banco de dados"
fake_users_db = {
    "usuario@exemplo.com": {
        "email": "usuario@exemplo.com",
        "hashed_password": pwd_context.hash("senha123"),
        "name": "Usuário Exemplo",
    }
}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    user: dict


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = fake_users_db.get(payload.email)
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    return {
        "message": "Login realizado com sucesso",
        "user": {
            "email": user["email"],
            "name": user["name"],
        },
    }