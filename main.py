from typing import List

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Создание объекта FastAPI
app = FastAPI(title='Лабораторная работа №4')


# Настройка базы данных MySQL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://isp_p_Morozova:12345@77.91.86.135/isp_p_Morozova"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Определение модели SQLAlchemy для пользователя

class Bank(Base):
    __tablename__ = 'banks'

    id = Column(Integer, primary_key=True)
    bankCode = Column(String(9))
    bankName = Column(String(100))
    legalAddress = Column(String(100))

    atms = relationship('ATM', back_populates='bank')
    clients = relationship('Client', back_populates='bank')

class ATM(Base):
    __tablename__ = 'atms'

    id = Column(Integer, primary_key=True)
    atmNumber = Column(String(16))
    atmAddress = Column(String(100))
    bankId = Column(Integer, ForeignKey('banks.id'))

    bank = relationship('Bank', back_populates='atms')
    operations = relationship('CashWithdrawal', back_populates='atm')

class Client(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True)
    cardNumber = Column(String(10))
    fullName = Column(String(100))
    address = Column(String(100))
    bankId = Column(Integer, ForeignKey('banks.id'))

    bank = relationship('Bank', back_populates='clients')
    operations = relationship('CashWithdrawal', back_populates='client')

class CashWithdrawal(Base):
    __tablename__ = 'cash_withdrawals'

    id = Column(Integer, primary_key=True)
    clientId = Column(Integer, ForeignKey('clients.id'))
    atmId = Column(Integer, ForeignKey('atms.id'))
    date = Column(DateTime)
    time = Column(DateTime)
    commission = Column(Boolean)
    amount = Column(Integer)

    client = relationship('Client', back_populates='operations')
    atm = relationship('ATM', back_populates='operations')


# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Определение Pydantic модели для пользователя
class Bank(BaseModel):
    id: int
    bankCode: str
    bankName: str
    legalAddress: str
    atms: list = []
    clients: list = []

class ATM(BaseModel):
    id: int
    atmNumber: str
    atmAddress: str
    bankId: int
    operations: list = []

class Client(BaseModel):
    id: int
    cardNumber: str
    fullName: str
    address: str
    bankId: int
    operations: list = []

class CashWithdrawal(BaseModel):
    id: int
    clientId: int
    atmId: int
    date: str = None
    time: str = None
    commission: bool = False
    amount: int

# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Маршрут для получения банка по ID
@app.get("/banks/{bank_id}", response_model=Bank)
def read_bank(bank_id: int, db: Session = Depends(get_db)):
    bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if bank is None:
        raise HTTPException(status_code=404, detail="Банк не найден")
    return bank

# Маршрут для создания нового банка
@app.post("/banks/", response_model=Bank)
def create_bank(bank: Bank, db: Session = Depends(get_db)):
    db_bank = Bank(**bank.dict())  # Создаем новый банк на основе полученных данных
    db.add(db_bank)
    db.commit()
    db.refresh(db_bank)
    return db_bank

# Обновление информации о банке
@app.put("/banks/{bank_id}", response_model=Bank)
def update_bank(bank_id: int, bank: Bank, db: Session = Depends(get_db)):
    db_bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if db_bank is None:
        raise HTTPException(status_code=404, detail="Банк не найден")
    for var, value in bank.dict().items():
        setattr(db_bank, var, value) if value is not None else None
    db.commit()
    db.refresh(db_bank)
    return db_bank
# Удаление банкомата
@app.delete("/atms/{atm_id}")
def delete_atm(atm_id: int, db: Session = Depends(get_db)):
    atm = db.query(ATM).filter(ATM.id == atm_id).first()
    if atm is None:
        raise HTTPException(status_code=404, detail="Банкомат не найден")
    db.delete(atm)
    db.commit()
    return {"message": "ATM deleted"}

# Получение всех банкоматов с указанным номером
@app.get("/atms/number/{atm_number}", response_model=List[ATM])
def read_atms_by_number(atm_number: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    atms = db.query(ATM).filter(ATM.atmNumber == atm_number).offset(skip).limit(limit).all()
    return atms


# Добавление нового клиента
@app.post("/clients/", response_model=Client)
def create_client(client: Client, db: Session = Depends(get_db)):
    db_client = Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

# Удаление клиента
@app.delete("/clients/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    db.delete(client)
    db.commit()
    return {"message": "Client deleted"}

# Добавление клиента к банку
@app.post("/banks/{bank_id}/atms/{atm_number}")
def add_atm_to_bank(bank_id: int, atm_number: str, db: Session = Depends(get_db)):
    bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if bank is None:
        raise HTTPException(status_code=404, detail="Банк не найден")
    atm = db.query(ATM).filter(ATM.atmNumber == atm_number).first()
    if atm is None:
        raise HTTPException(status_code=404, detail="Банкомат не найден")
    bank.atms.append(atm)
    db.commit()
    return {"message": "ATM added to bank"}


# Получение всех клиентов по ID банка
@app.get("/banks/{bank_id}/clients", response_model=List[Client])
def read_bank_clients(bank_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    clients = db.query(Client).filter(Client.bankId == bank_id).offset(skip).limit(limit).all()
    return clients

# Получение всех клиентов с указанным номером карты
@app.get("/clients/card/{card_number}", response_model=List[Client])
def read_clients_by_card_number(card_number: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    clients = db.query(Client).filter(Client.cardNumber == card_number).offset(skip).limit(limit).all()
    return clients


# Добавление новой операции
@app.post("/operations/", response_model=CashWithdrawal)
def create_operation(operation: CashWithdrawal, db: Session = Depends(get_db)):
    db_operation = CashWithdrawal(**operation.dict())
    db.add(db_operation)
    db.commit()
    db.refresh(db_operation)
    return db_operation

# Удаление операции
@app.delete("/operations/{operation_id}")
def delete_operation(operation_id: int, db: Session = Depends(get_db)):
    operation = db.query(CashWithdrawal).filter(CashWithdrawal.id == operation_id).first()
    if operation is None:
        raise HTTPException(status_code=404, detail="Операция не найдена")
    db.delete(operation)
    db.commit()
    return {"message": "Operation deleted"}

# Получение всех операций по ID банкомата
@app.get("/atms/{atm_id}/operations", response_model=List[CashWithdrawal])
def read_atm_operations(atm_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    operations = db.query(CashWithdrawal).filter(CashWithdrawal.atmId == atm_id).offset(skip).limit(limit).all()
    return operations

# Добавление операции к банкомату
@app.post("/atms/{atm_id}/operations")
def add_operation_to_atm(atm_id: int, operation: CashWithdrawal, db: Session = Depends(get_db)):
    atm = db.query(ATM).filter(ATM.id == atm_id).first()
    if atm is None:
        raise HTTPException(status_code=404, detail="Банкомат не найден")
    db_operation = CashWithdrawal(**operation.dict(), atmId=atm_id)
    db.add(db_operation)
    db.commit()
    db.refresh(db_operation)
    return db_operation

# Получение всех операций по ID клиента
@app.get("/clients/{client_id}/operations", response_model=List[CashWithdrawal])
def read_client_operations(client_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    operations = db.query(CashWithdrawal).filter(CashWithdrawal.clientId == client_id).offset(skip).limit(limit).all()
    return operations

# Получение всех операций с комиссией
@app.get("/operations/commission", response_model=List[CashWithdrawal])
def read_operations_with_commission(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    operations = db.query(CashWithdrawal).filter(CashWithdrawal.commission == True).offset(skip).limit(limit).all()
    return operations

# Добавление номера банкомата к банку
@app.post("/banks/{bank_id}/atms/{atm_number}")
def add_atm_to_bank(bank_id: int, atm_number: str, db: Session = Depends(get_db)):
    bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if bank is None:
        raise HTTPException(status_code=404, detail="Банк не найден")
    atm = db.query(ATM).filter(ATM.atmNumber == atm_number).first()
    if atm is None:
        raise HTTPException(status_code=404, detail="Банкомат не найден")
    bank.atms.append(atm)
    db.commit()
    return {"message": "ATM added to bank"}

# Добавление операции к клиенту
@app.post("/clients/{client_id}/operations")
def add_operation_to_client(client_id: int, operation: CashWithdrawal, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    db_operation = CashWithdrawal(**operation.dict(), clientId=client_id)
    db.add(db_operation)
    db.commit()
    db.refresh(db_operation)
    return db_operation





