# Arquitetura — Sprint 1

Modular monolith greenfield:

```text
backend/app/
├── core/           # config, security, permissions, exceptions
├── db/
└── modules/
    ├── auth/
    ├── org/        # companies, stores, departments, users
    └── queue/      # models, policies, services, routes
frontend/           # React + TS admin (filas / inspector)
```

Fonte da verdade: backend. Regras de prioridade em `QueueSelectionEngine`.  
Integrações Toledo/CISS: fora do escopo (desacopladas no roadmap).
