# 2. Architecture Constraints

## 2.1 Technical Constraints

| Constraint                         | Description                                                           |
|-----------------------------------|-----------------------------------------------------------------------|
| Python as Primary Language        | The system uses Python (Django) for the backend and PDF/A generation   |
| PostgreSQL Database               | PostgreSQL is used as the primary database system                      |
| Docker-based Deployment           | The system is packaged and deployed using Docker containers           |
| Kubernetes Support                | System must support Kubernetes orchestration for larger installations |
| ZUGFeRD 2.1/EN16931 Compliance    | The system must comply with ZUGFeRD 2.1/EN16931 standards             |

## 2.2 Organizational Constraints

| Constraint                       | Description                                                           |
|---------------------------------|-----------------------------------------------------------------------|
| Development Methodology         | Agile development with regular iterations                             |
| Documentation                   | Architecture documentation follows the arc42 template                  |
| Testing Requirements            | Unit tests required for all modules with defined coverage targets     |
| Code Reviews                    | All code changes require peer review before merging                   |

## 2.3 Political Constraints

| Constraint                       | Description                                                           |
|---------------------------------|-----------------------------------------------------------------------|
| Data Protection                 | Must comply with GDPR and other relevant data protection regulations   |
| German Legal Requirements       | Must comply with GoBD and other German accounting regulations         |
| Open Source Policy             | Preference for open-source libraries with compatible licenses          |
