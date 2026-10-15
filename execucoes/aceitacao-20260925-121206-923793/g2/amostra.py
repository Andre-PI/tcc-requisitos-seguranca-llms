from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Simulação de um banco de dados
fake_users_db = {
    "user@example.com": {
        "email": "user@example.com",
        "hashed_password": pwd_context.hash("secret123"),
        "name": "Usuário Exemplo"
    }
}

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    email: EmailStr
    name: str
    message: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    user = fake_users_db.get(data.email)
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    return LoginResponse(email=user["email"], name=user["name"], message="Login realizado com sucesso")