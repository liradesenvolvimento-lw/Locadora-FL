# Imagem base oficial do Python
FROM python:3.12-slim

# Define o diretório de trabalho dentro do servidor
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para o servidor
COPY . .

# Expõe a porta padrão da API
EXPOSE 8000

# Comando para iniciar o servidor Uvicorn em produção
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]