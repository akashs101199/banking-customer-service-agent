# Banking Customer Service Agentic AI 🏦🤖

> **🚧 WORK IN PROGRESS 🚧**
> This project is currently in active development. Features and APIs are subject to change.

A fully autonomous banking customer service system powered by open-source AI agents. This system handles account creation, transactions, card services, KYC verification, and all banking processes **without human intervention**.

## 🌟 Features

### Autonomous Banking Operations
- **Account Management**: Create accounts, verify KYC, manage customer profiles
- **Transaction Processing**: View history, transfer funds, check balances
- **Card Services**: Apply for credit/debit cards, activate, block/unblock
- **Loan Services**: Inquire about loans, check eligibility
- **Fraud Detection**: Automated fraud scoring and alerts
- **Compliance**: Built-in KYC/AML screening and audit logging

### AI-Powered Agents
- **CrewAI Integration**: Collaborative role-based agents (Senior Banker, Transaction Specialist, etc.)
- **Multi-Agent Architecture**: Specialized agents for different banking domains
- **Intent Classification**: Automatic routing to appropriate agents
- **Conversation Memory**: Context-aware responses using semantic search
- **LLM Integration**: Local LLM deployment via Ollama (fully open source)

### Security & Compliance
- **Data Encryption**: Sensitive data encrypted at rest
- **Audit Logging**: Comprehensive logging of all operations
- **JWT Authentication**: Secure API access
- **Fraud Detection**: Real-time transaction monitoring

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│                  (Chat Interface / API)                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              Agentic AI Orchestrator (LangGraph)             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Intent Classifier → Route to Specialized Agent     │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│ Account Agent  │  │ Transaction │  │  Card Services  │
│                │  │    Agent    │  │     Agent       │
│ • Create Acc   │  │ • History   │  │ • Credit Card   │
│ • KYC Verify   │  │ • Details   │  │ • Debit Card    │
│ • Update Info  │  │ • Transfer  │  │ • Verification  │
└───────┬────────┘  └──────┬──────┘  └────────┬────────┘
        │                  │                   │
        └──────────────────┼───────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              Banking Services Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Database │  │ Security │  │  Fraud   │             │
│  │ Service  │  │ Service  │  │ Detection│             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

### AI & LLM
- **CrewAI**: Role-based agent orchestration
- **LangChain**: Agent orchestration and LLM integration
- **LangGraph**: Multi-agent workflow management
- **Ollama**: Local LLM deployment (Llama 3.1 / Mistral)
- **ChromaDB**: Vector database for semantic search

### Backend
- **FastAPI**: REST API framework
- **PostgreSQL**: Relational database
- **SQLAlchemy**: ORM
- **Pydantic**: Data validation

### Security
- **Cryptography**: Data encryption
- **Passlib**: Password hashing
- **python-jose**: JWT tokens

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 14+
- Ollama (for local LLM)
- 8GB+ RAM recommended

## 🚀 Quick Start

### 1. Install Ollama and Pull Model

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve

# Pull Llama 3.1 model (in another terminal)
ollama pull llama3.1:8b
```

### 2. Set Up Database

```bash
# Install PostgreSQL (macOS)
brew install postgresql@14
brew services start postgresql@14

# Create database
createdb banking_ai

# Create user
psql -d banking_ai -c "CREATE USER bankingai WITH PASSWORD 'bankingai123';"
psql -d banking_ai -c "GRANT ALL PRIVILEGES ON DATABASE banking_ai TO bankingai;"
```

### 3. Install Dependencies

```bash
# Clone the repository
cd /Users/admin/Desktop/projects/banking-customer-service-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 5. Initialize Database

```bash
# Run database initialization
python -c "from database.connection import init_database; init_database()"
```

### 6. Start the Application

```bash
# Start FastAPI server
python api/main.py

# Or use uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 💬 Usage Examples

### Chat API

```bash
# Simple chat request
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to open a savings account",
    "session_id": "user123"
  }'
```

### Python Client

```python
import requests

# Chat with the AI
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": "What's my account balance?",
        "session_id": "user123",
        "context": {
            "account_number": "ACC1234567890"
        }
    }
)

print(response.json()["answer"])
```

### Example Conversations

**Account Creation:**
```
User: I want to open a new savings account
AI: I'd be happy to help you open a savings account! To get started, I'll need some information...

User: My name is John Doe, email john@example.com
AI: ✅ Great news! Your account has been created successfully.
    Account Number: ACC1234567890
    Next steps: Complete KYC verification...
```

**Balance Inquiry:**
```
User: What's my balance?
AI: 💰 Account Balance Information
    Account: ACC1234567890 (Savings)
    Current Balance: USD 5,250.00
    Available Balance: USD 5,250.00
```

**Card Application:**
```
User: I need a credit card
AI: ✅ Credit Card Application Approved!
    Card Number: **** **** **** 1234
    Credit Limit: USD 5,000.00
    Your card will be delivered within 5-7 business days.
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov=services --cov-report=html

# Run specific test file
pytest tests/test_agents.py -v
```

## 📁 Project Structure

```
banking-customer-service-agent/
├── agents/                      # AI Agents
│   ├── base_agent.py           # Base agent class
│   ├── orchestrator.py         # Main orchestrator (LangGraph)
│   ├── intent_classifier.py    # Intent classification
│   ├── memory.py               # Conversation memory (ChromaDB)
│   ├── account_agent.py        # Account operations
│   ├── transaction_agent.py    # Transaction operations
│   └── card_agent.py           # Card operations
├── api/                         # FastAPI Application
│   └── main.py                 # API endpoints
├── database/                    # Database Layer
│   ├── models.py               # SQLAlchemy models
│   ├── connection.py           # DB connection management
│   └── schema.sql              # PostgreSQL schema
├── security/                    # Security Modules
│   ├── encryption.py           # Data encryption
│   ├── authentication.py       # JWT & password hashing
│   └── audit_logger.py         # Audit logging
├── utils/                       # Utilities
│   └── llm_client.py           # Ollama LLM client
├── config.py                    # Configuration management
├── requirements.txt             # Python dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

## 🔒 Security Features

### Data Protection
- **Encryption at Rest**: Sensitive data (card numbers, CVV, SSN) encrypted using Fernet
- **Password Hashing**: Bcrypt for password and PIN hashing
- **Data Masking**: Card numbers and SSNs masked in responses

### Authentication & Authorization
- **JWT Tokens**: Secure API access with access and refresh tokens
- **Session Management**: Secure session handling with expiration

### Audit & Compliance
- **Comprehensive Logging**: All operations logged with full audit trail
- **Fraud Detection**: Real-time transaction monitoring
- **KYC/AML**: Built-in compliance checks

## 🎯 Supported Operations

### Account Services
- ✅ Account creation (savings, checking, business)
- ✅ KYC verification and document processing
- ✅ Account inquiry and details
- ✅ Account status management

### Transaction Services
- ✅ Balance inquiry
- ✅ Transaction history (with filters)
- ✅ Transaction details
- ✅ Fund transfers
- ✅ Bill payments

### Card Services
- ✅ Credit card application
- ✅ Debit card application
- ✅ Card activation
- ✅ Card blocking/unblocking
- ✅ Card inquiry and limits

### Additional Services
- ✅ Loan inquiries
- ✅ Statement generation
- ✅ Fraud alerts
- ✅ General banking support

## 🔧 Configuration

Key configuration options in `.env`:

```bash
# LLM Settings
OLLAMA_MODEL=llama3.1:8b          # Model to use
OLLAMA_TEMPERATURE=0.7            # Response creativity

# Security
SECRET_KEY=your-secret-key        # JWT secret
ENCRYPTION_KEY=your-encryption-key # Data encryption key

# Fraud Detection
FRAUD_DETECTION_ENABLED=true
FRAUD_SCORE_THRESHOLD=0.7
MAX_DAILY_TRANSACTION_AMOUNT=50000

# KYC
KYC_AUTO_APPROVAL_THRESHOLD=0.85
KYC_REQUIRED_DOCUMENTS=id_proof,address_proof,photo
```

## 📊 Monitoring & Observability

### Health Check
```bash
curl http://localhost:8000/health
```

### System Stats
```bash
curl http://localhost:8000/stats
```

### Logs
Logs are written to `./logs/banking_ai.log` in JSON format for easy parsing.

## 🚧 Limitations & Future Enhancements

### Current Limitations
- Mock banking backend (not connected to real core banking)
- Simplified KYC verification (OCR not fully implemented)
- Basic fraud detection rules

### Planned Enhancements
- [ ] Real-time notifications (email, SMS)
- [ ] Advanced fraud detection with ML models
- [ ] Multi-language support
- [ ] Voice interface integration
- [ ] Mobile app integration
- [ ] Advanced analytics dashboard

## 🤝 Contributing

This is a demonstration project. For production use:
1. Integrate with real core banking systems
2. Implement proper KYC/AML compliance
3. Add comprehensive security testing
4. Set up monitoring and alerting
5. Implement disaster recovery

## 📄 License

This project is for educational and demonstration purposes.

## 🙏 Acknowledgments

Built with open-source technologies:
- LangChain & LangGraph
- Ollama
- FastAPI
- PostgreSQL
- ChromaDB

## 📞 Support

For issues or questions:
1. Check the documentation at `/docs`
2. Review the API reference at `/redoc`
3. Check system health at `/health`

---

**Note**: This is a demonstration system. For production banking applications, ensure compliance with all relevant financial regulations, security standards (PCI DSS), and data protection laws (GDPR, etc.).
