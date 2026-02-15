#!/bin/bash
# Setup script para Ollama

set -e

echo "=== Ollama Setup Script ==="

# Verificar que Ollama está instalado
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✓ Ollama already installed"
fi

# Iniciar servicio Ollama
echo "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!
sleep 5

# Descargar modelos
echo "Pulling models..."
ollama pull llama3.2
ollama pull mistral

echo "✓ Ollama setup complete"
echo "Ollama PID: $OLLAMA_PID"
