# 🐧 Conversational Looker Agent

## ✅ ESTADO ACTUAL - FUNCIONAL
**Fecha: 2025-09-25 | Estado: Bot de Slack funcionando con integración Looker real**

Conversational AI agent que traduce consultas en lenguaje natural a queries de Looker para análisis de datos empresariales.

## 🚀 LO QUE FUNCIONA HOY:
- ✅ **Slack Bot**: Responde a mentions `@bot` y mensajes directos
- ✅ **Seguridad**: Solo responde a usuarios autorizados
- ✅ **Looker API Real**: Integración completa con consumer_sessions explore
- ✅ **Schema Completo**: 61 dimensiones, 1 medida cargadas
- ✅ **DSPy Pipeline**: 8 intenciones preparadas (actualmente en bypass)
- ✅ **Environment**: Todas las credenciales configuradas

## 🎯 PROGRESO ACTUAL:
**Objetivo**: Activar pipeline DSPy para respuestas inteligentes
- ✅ Probar DSPy con CLI (`python app.py`)
- ✅ Reactivar `agent.process_query()` en Slack
- [ ] Validar intent detection funcionando
- [ ] Primera query real a Looker API

## Features
- **Natural Language Processing**: Uses DSPy for intent detection and query curation
- **Conversation Memory**: Tracks user preferences and conversation context
- **Query Recipes**: Predefined patterns for common data queries
- **Looker Integration**: Placeholder API client ready for real Looker connection
- **Interactive CLI**: Simple command-line interface for testing

## 🚀 Quick Start

### ✅ Ejecutar el Bot de Slack (FUNCIONAL HOY):
```bash
# 1. Instalar dependencias (si es primera vez)
pip install -r requirements.txt

# 2. Verificar .env configurado
# (ya está listo con todas las credenciales)

# 3. Ejecutar bot de Slack
python slack_app.py
```

### 💬 Usar el Bot:
- **En canal**: `@bot hello`
- **Mensaje directo**: `hello`
- **Comandos disponibles**:
  - `hello` → Saludo
  - `help` / `what can you do` → Ayuda
  - `show me data` → Info sobre queries

### 🛑 Terminar la App:
- **Ctrl+C una vez**: Shutdown limpio
- **Ctrl+C dos veces**: Force exit

### 🖥️ Modo CLI (Para testing DSPy próximamente):
```bash
# CLI interactivo para probar DSPy directamente
python app.py
```

## Project Structure
```
clone/
├── src/
│   ├── modules/
│   │   ├── agent/           # Main conversational agent
│   │   └── signatures/      # DSPy signature modules
│   ├── memory/              # Conversation memory system
│   ├── looker/              # Looker API integration
│   └── __init__.py
├── config/
│   ├── agent_config.yaml    # Main configuration
│   └── looker_recipes.json  # Query pattern recipes
├── tests/                   # Unit tests
├── app.py                   # CLI application
└── requirements.txt
```

## Key Components

### Conversation Flow
1. **Intent Detection** (`TriageSignature`): Determines user intent from natural language
2. **Query Curation** (`QueryCuratorSignature`): Matches queries to predefined recipes
3. **Query Building** (`LookerQueryBuilder`): Converts intent to Looker API queries
4. **Response Synthesis** (`ResponseSynthesizerSignature`): Creates natural language responses
5. **Memory Management** (`ConversationMemory`): Tracks context and user preferences

### Intent Types
- `GATHER_DATA_FROM_LOOKER`: Query Looker for data
- `GET_EXECUTIVE_SUMMARY`: Summarize recent conversation data
- `DRILL_DOWN_ANALYSIS`: Filter/segment existing data
- `AGENT_CAPABILITIES`: Ask about agent features
- `DATA_SOURCE_INFO`: Learn about available data
- `FRIENDLY_CONVERSATION`: Casual interaction
- `MANAGE_CONVERSATION`: Clear history, start fresh

### Sample Queries
- "Show me revenue by country"
- "What are the trends over time?"
- "Top 10 products by revenue"
- "Give me an executive summary"
- "What data sources are available?"

## Development

### Running Tests
```bash
pytest tests/
```

### Mock Mode
For development without real Looker credentials, the agent runs in mock mode by default, returning sample data for testing conversation flow.

### Adding New Recipes
Edit `config/looker_recipes.json` to add new query patterns:
```json
{
  "name": "new_recipe",
  "description": "Description of the recipe",
  "triggers": ["keyword1", "keyword2"],
  "query_template": {
    "dimensions": ["dimension_name"],
    "measures": ["measure_name"],
    "limit": 10
  }
}
```

## Implementation Plan

**Current Goal**: Create deterministic NL → JSON mapping using DSPy signatures with real Looker API

### 🚀 5-Phase Implementation:
1. **Phase 1: Preparation Base** ← CURRENT
   - Migrate real LookerService with authentication
   - Copy consumer_sessions schema JSON
   - Update configuration for real API connection

2. **Phase 2: Intent Integration**
   - Map DSPy intents to Looker query types
   - Create improved LookerQueryBuilder
   - Implement deterministic NL→JSON mapping

3. **Phase 3: Advanced DSPy Signatures**
   - LookerFieldMappingSignature
   - LookerFilterSignature
   - QueryValidationSignature

4. **Phase 4: Context & Guard-rails**
   - Inject full schema as context
   - Add examples for each measure/dimension
   - Pre-query validation

5. **Phase 5: Optimization**
   - Caching and performance
   - Enhanced conversational responses
   - End-to-end Slack integration

---

## 📋 **8 Intenciones DSPy (Listas para activar):**
1. **`GATHER_DATA_FROM_LOOKER`**: Queries principales ("show me revenue")
2. **`GET_EXECUTIVE_SUMMARY`**: Análisis de datos existentes
3. **`DRILL_DOWN_ANALYSIS`**: Filtros/segmentación
4. **`AGENT_CAPABILITIES`**: Info sobre capacidades del bot
5. **`DATA_SOURCE_INFO`**: Información sobre datos disponibles
6. **`FRIENDLY_CONVERSATION`**: Saludos y conversación casual
7. **`MANAGE_CONVERSATION`**: Limpiar historial, empezar de nuevo
8. **`OTHER`**: Fallback para queries no reconocidas

## 📁 **Archivos Clave:**

### ✅ **Funcionales:**
- `slack_app.py` - Entry point principal
- `src/slack/slack_service1.py` - Event handlers
- `src/looker/service.py` - LookerService real
- `src/modules/agent/conversational_agent.py` - DSPy pipeline

### 📊 **Configuración:**
- `.env` - Credenciales (configurado)
- `config/consumer_sessions_explore.json` - Schema Looker
- `config/agent_config.yaml` - Configuración DSPy

**📋 Ver `NEXT_STEPS.md` para próximos pasos detallados**