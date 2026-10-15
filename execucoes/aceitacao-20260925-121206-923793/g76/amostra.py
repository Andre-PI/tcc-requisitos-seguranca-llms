from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Exemplo de "banco" em memória
fake_users_db = {
    "usuario@exemplo.com": {
        "email": "usuario@exemplo.com",
        "hashed_password": pwd_context.hash("senha123"),
    }
}

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    message: str
    email: EmailStr

@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    user = fake_users_db.get(data.email)
    if not user or not pwd_context.verify(data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )

    return LoginResponse(message="Login realizado com sucesso", email=user["email"])