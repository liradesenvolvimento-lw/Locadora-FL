from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

# TRANSPORTADORA
class TransportadoraBase(BaseModel):
    razao_social: str
    nome_fantasia: Optional[str] = None
    cnpj: str
    email: str
    telefone: str
    responsavel_nome: Optional[str] = None

class TransportadoraCreate(TransportadoraBase):
    pass

class TransportadoraResponse(TransportadoraBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# VEÍCULO FLEXÍVEL
class VeiculoBase(BaseModel):
    placa: str
    categoria: str = "Utilitário Leve"
    modelo: str
    marca: Optional[str] = "Fiat"
    ano: int
    capacidade_carga_kg: Optional[float] = 650.0
    chassi: Optional[str] = None
    km_atual: int = 0
    km_ultima_revisao: int = 0
    status: str = "DISPONIVEL"

class VeiculoCreate(VeiculoBase):
    pass

class VeiculoResponse(VeiculoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# CONTRATO
class ContratoBase(BaseModel):
    veiculo_id: int
    transportadora_id: int
    km_inicial: int
    franquia_km_mensal: int
    valor_km_excedente: float = 0.50
    valor_mensalidade: float
    dia_vencimento_fatura: int
    data_inicio: date
    data_fim: Optional[date] = None
    status: str = "ATIVO"

class ContratoCreate(ContratoBase):
    pass

class ContratoResponse(ContratoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# CHECKLIST COMPLETO (CHECK-OUT / CHECK-IN)
class ChecklistBase(BaseModel):
    veiculo_id: int
    contrato_id: Optional[int] = None
    tipo: str # CHECKOUT_SAIDA, CHECKIN_RETORNO, VISTORIA_ROTINA
    km_registrado: int
    nivel_combustivel: str
    crlv_ok: bool = True
    manual_ok: bool = True
    cartao_seguro_ok: bool = True
    estepe_ok: bool = True
    kit_ferramentas_ok: bool = True
    pneus_sulco_ok: bool = True
    limpeza_interna_ok: bool = True
    luzes_farois_ok: bool = True
    ar_condicionado_ok: bool = True
    avarias_observacoes: Optional[str] = None
    foto_evidencia_base64: Optional[str] = None

class ChecklistCreate(ChecklistBase):
    pass

class ChecklistResponse(ChecklistBase):
    id: int
    data_registro: datetime
    class Config:
        from_attributes = True

# CUSTO FIXO COM FILTRO TEMPORAL
class CustoFixoBase(BaseModel):
    veiculo_id: int
    descricao: str
    tipo_custo: str
    valor_mensal: float
    dia_vencimento: int
    mes_referencia: Optional[int] = None
    ano_referencia: Optional[int] = None
    parcelas_totais: int = 1
    parcela_atual: int = 1
    status: str = "ATIVO"

class CustoFixoCreate(CustoFixoBase):
    pass

class CustoFixoResponse(CustoFixoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True