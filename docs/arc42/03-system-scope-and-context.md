# 3. System Scope and Context

## 3.1 Business Context

The eRechnung system interacts with various external systems and users:

| Actor/System                | Description of Interaction                                                |
|-----------------------------|---------------------------------------------------------------------------|
| **Business Users**          | Create, view, and manage invoices through the admin interface             |
| **External ERP Systems**    | Send invoice data to the system and receive processed invoices via API    |
| **Tax Authorities**         | May receive e-invoices in legally mandated formats                        |
| **Business Partners**       | Receive generated e-invoices and PDF documents                            |
| **Auditors**                | Access invoice history and audit trails during reviews                    |

## 3.2 Technical Context

From a technical perspective, the system interfaces with:

| Technical System/Component     | Interface                                                               |
|-------------------------------|-------------------------------------------------------------------------|
| **Client Applications**       | REST APIs secured with JWT authentication                                |
| **PostgreSQL Database**       | Database connection for persistent storage                               |
| **External Authentication**   | Optional integration with SSO systems                                    |
| **Email Servers**             | SMTP for sending invoices and notifications                              |
| **Storage Systems**           | For document storage (PDF/A and XML files)                               |

## 3.3 External Interface Specifications

### 3.3.1 API Interfaces

The system exposes REST APIs with the following characteristics:
- OpenAPI/Swagger documentation
- JWT-based authentication
- JSON and XML response formats
- Standard HTTP status codes and error responses

### 3.3.2 File Format Interfaces

The system produces and processes files in the following formats:
- ZUGFeRD 2.1/EN16931 XML
- PDF/A-3 with embedded XML
- JSON for data exchange
