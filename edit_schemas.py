"""Validation for edits; omitted fields remain untouched, explicit null clears optional fields."""
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator
import schemas


class VeiculoEdit(schemas.VeiculoBase):
    placa: str = Field(min_length=1, max_length=8)
    categoria: str = Field(min_length=1, max_length=50)
    modelo: str = Field(min_length=1, max_length=100)
    marca: Optional[str] = Field(None, max_length=50)
    chassi: Optional[str] = Field(None, max_length=17)
    ano: int = Field(ge=1900, le=2100)
    capacidade_carga_kg: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    km_atual: int = Field(ge=0)
    km_ultima_revisao: int = Field(ge=0)
    status: Literal['DISPONIVEL', 'ALOCADO', 'MANUTENCAO']

    @model_validator(mode='after')
    def revisar_km(self):
        if self.km_ultima_revisao > self.km_atual:
            raise ValueError('KM da última revisão não pode superar o KM atual.')
        return self


class TransportadoraEdit(schemas.TransportadoraBase):
    razao_social: str = Field(min_length=1, max_length=150)
    nome_fantasia: Optional[str] = Field(None, max_length=100)
    cnpj: str = Field(min_length=1, max_length=18)
    email: str = Field(min_length=1, max_length=100)
    telefone: str = Field(min_length=1, max_length=20)
    responsavel_nome: Optional[str] = Field(None, max_length=100)


class ContratoEdit(schemas.ContratoBase):
    veiculo_id: int = Field(gt=0)
    transportadora_id: int = Field(gt=0)
    km_inicial: int = Field(ge=0)
    franquia_km_mensal: int = Field(ge=0)
    valor_km_excedente: float = Field(ge=0, allow_inf_nan=False)
    valor_mensalidade: float = Field(ge=0, allow_inf_nan=False)
    dia_vencimento_fatura: int = Field(ge=1, le=31)
    status: Literal['ATIVO', 'FINALIZADO', 'CANCELADO']

    @model_validator(mode='after')
    def revisar_datas(self):
        if self.data_fim and self.data_fim < self.data_inicio:
            raise ValueError('Data final não pode ser anterior à data inicial.')
        return self


class ChecklistEdit(schemas.ChecklistBase):
    veiculo_id: int = Field(gt=0)
    contrato_id: Optional[int] = Field(None, gt=0)
    km_registrado: int = Field(ge=0)
    tipo: Literal['CHECKOUT_SAIDA', 'CHECKIN_RETORNO', 'VISTORIA_ROTINA']
    nivel_combustivel: Literal['RESERVA', '1/4', '1/2', '3/4', 'CHEIO']


class CustoEdit(schemas.CustoFixoBase):
    veiculo_id: int = Field(gt=0)
    descricao: str = Field(min_length=1, max_length=100)
    tipo_custo: str = Field(min_length=1, max_length=50)
    valor_mensal: float = Field(ge=0, allow_inf_nan=False)
    dia_vencimento: int = Field(ge=1, le=31)
    mes_referencia: Optional[int] = Field(None, ge=1, le=12)
    ano_referencia: Optional[int] = Field(None, ge=1900, le=2100)
    parcelas_totais: int = Field(ge=1)
    parcela_atual: int = Field(ge=1)
    status: Literal['ATIVO', 'INATIVO']

    @model_validator(mode='after')
    def revisar_parcelas(self):
        if self.parcela_atual > self.parcelas_totais:
            raise ValueError('Parcela atual não pode superar o total de parcelas.')
        return self


class PartialEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')


def partial(model):
    # Full validation runs after merging the patch with the stored record.
    return create_model(model.__name__ + 'Patch', __base__=PartialEdit, **{
        name: (Optional[field.annotation], None)
        for name, field in model.model_fields.items()
    })


VeiculoPatch = partial(VeiculoEdit)
TransportadoraPatch = partial(TransportadoraEdit)
ContratoPatch = partial(ContratoEdit)
ChecklistPatch = partial(ChecklistEdit)
CustoPatch = partial(CustoEdit)
