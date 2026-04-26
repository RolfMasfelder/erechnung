# 5. Building Block View

## 5.1 Overall System

The eRechnung system consists of the following high-level building blocks:

### Level 1: System Context

```
┌─────────────────────────────────────────┐
│             eRechnung System            │
│                                         │
│  ┌───────────────┐   ┌───────────────┐  │
│  │ Django App    │   │ PostgreSQL DB │  │
│  │ (APIs + Admin)│   │               │  │
│  └───────────────┘   └───────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

## 5.2 Level 2: Container View

```
┌─────────────────────────────────────────────────────────────┐
│                     eRechnung System                        │
│                                                             │
│  ┌───────────────────┐        ┌────────────────────────┐    │
│  │   Django App      │        │   PostgreSQL Database  │    │
│  │                   │        │                        │    │
│  │  ┌─────────────┐  │        │  ┌──────────────────┐  │    │
│  │  │ REST APIs   │  │◄─────► │  │   Data Storage   │  │    │
│  │  └─────────────┘  │        │  └──────────────────┘  │    │
│  │                   │        │                        │    │
│  │  ┌─────────────┐  │        └────────────────────────┘    │
│  │  │ Admin UI    │  │                                      │
│  │  └─────────────┘  │                                      │
│  │                   │                                      │
│  │  ┌─────────────┐  │                                      │
│  │  │ PDF/A Gen   │  │                                      │
│  │  └─────────────┘  │                                      │
│  │                   │                                      │
│  └───────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 5.3 Level 3: Detailed Component View

### 5.3.1 Django Application Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Django Application                                 │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   API Gateway   │  │  Authentication │  │   Admin UI      │                  │
│  │   (DRF Router)  │  │   & Security    │  │   Controllers   │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
│           │                     │                     │                        │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                         Business Logic Layer                                ││
│  │                                                                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        ││
│  │  │ Invoice     │  │ BizPartner  │  │ PDF/A       │  │ ZUGFeRD     │        ││
│  │  │ Service     │  │ Service     │  │ Generator   │  │ Service     │        ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        ││
│  │                                                                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        ││
│  │  │ Validation  │  │ Audit &     │  │ Encryption  │  │ Compliance  │        ││
│  │  │ Service     │  │ Logging     │  │ Service     │  │ Service     │        ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│           │                     │                     │                        │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                         Data Access Layer                                   ││
│  │                                                                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        ││
│  │  │ Invoice     │  │ BizPartner  │  │ Product     │  │ User        │        ││
│  │  │ Repository  │  │ Repository  │  │ Repository  │  │ Repository  │        ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        ││
│  │                                                                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        ││
│  │  │ Audit Log   │  │ File Storage│  │ Cache       │  │ Queue       │        ││
│  │  │ Repository  │  │ Repository  │  │ Repository  │  │ Repository  │        ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.3.2 Core Data Models and Relationships

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               Data Model Layer                                  │
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │     Company     │    │  BusinessPartner │    │     Product     │              │
│  │─────────────────│    │─────────────────│    │─────────────────│              │
│  │ + id            │    │ + id            │    │ + id            │              │
│  │ + name          │    │ + company_name  │    │ + name          │              │
│  │ + tax_number    │    │ + contact_info  │    │ + description   │              │
│  │ + address       │    │ + billing_addr  │    │ + unit_price    │              │
│  │ + bank_details  │    │ + tax_number    │    │ + tax_rate      │              │
│  │ + settings      │    │ + payment_terms │    │ + category      │              │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘              │
│          │                       │                       │                     │
│          │                       │                       │                     │
│          └───────────────┐       │       ┌───────────────┘                     │
│                          │       │       │                                     │
│                          ▼       ▼       ▼                                     │
│                    ┌─────────────────────────────────────┐                     │
│                    │              Invoice                │                     │
│                    │─────────────────────────────────────│                     │
│                    │ + id                                │                     │
│                    │ + invoice_number                    │                     │
│                    │ + issue_date                        │                     │
│                    │ + due_date                          │                     │
│                    │ + status (draft/sent/paid/overdue)  │                     │
│                    │ + total_amount                      │                     │
│                    │ + tax_amount                        │                     │
│                    │ + currency                          │                     │
│                    │ + zugferd_profile                   │                     │
│                    │ + pdf_file_path                     │                     │
│                    │ + xml_file_path                     │                     │
│                    │ + digital_signature                 │                     │
│                    │ + company_id (FK)                   │                     │
│                    │ + business_partner_id (FK)                  │                     │
│                    └─────────────────────────────────────┘                     │
│                                    │                                           │
│                                    │                                           │
│                                    ▼                                           │
│                    ┌─────────────────────────────────────┐                     │
│                    │           InvoiceItem               │                     │
│                    │─────────────────────────────────────│                     │
│                    │ + id                                │                     │
│                    │ + line_number                       │                     │
│                    │ + quantity                          │                     │
│                    │ + unit_price                        │                     │
│                    │ + tax_rate                          │                     │
│                    │ + total_amount                      │                     │
│                    │ + description                       │                     │
│                    │ + invoice_id (FK)                   │                     │
│                    │ + product_id (FK)                   │                     │
│                    └─────────────────────────────────────┘                     │
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │   AuditLog      │    │    UserRole     │    │   SystemConfig  │              │
│  │─────────────────│    │─────────────────│    │─────────────────│              │
│  │ + id            │    │ + id            │    │ + id            │              │
│  │ + timestamp     │    │ + name          │    │ + key           │              │
│  │ + user_id       │    │ + permissions   │    │ + value         │              │
│  │ + action        │    │ + description   │    │ + encrypted     │              │
│  │ + entity_type   │    │ + is_active     │    │ + category      │              │
│  │ + entity_id     │    └─────────────────┘    │ + environment   │              │
│  │ + old_values    │                           └─────────────────┘              │
│  │ + new_values    │                                                           │
│  │ + ip_address    │                                                           │
│  └─────────────────┘                                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 5.4 Component Descriptions

### 5.4.1 API Gateway (DRF Router)
- Centralized entry point for all API requests
- Request routing and load balancing
- Rate limiting and throttling
- API versioning management
- Request/response logging and monitoring

### 5.4.2 Authentication & Security Layer
- JWT token validation and management
- Multi-factor authentication (MFA)
- Role-based access control (RBAC)
- Session management and timeout
- Security headers and CORS handling

### 5.4.3 Business Logic Services
- **Invoice Service**: Core invoice lifecycle management
- **BusinessPartner Service**: Business partner data and relationship management
- **PDF/A Generator**: Compliant PDF/A-3 document creation
- **ZUGFeRD Service**: XML generation and validation
- **Validation Service**: Business rule and data validation
- **Encryption Service**: Data encryption and key management

### 5.4.4 Data Access Layer
- Repository pattern implementation
- Database connection pooling
- Query optimization and caching
- Transaction management
- Data migration and versioning

### 5.4.5 Security Components
- **Encryption Service**: AES-256 encryption for sensitive data
- **Audit Service**: Comprehensive audit trail logging
- **Compliance Service**: Regulatory compliance validation
- **Key Management**: Secure key storage and rotation
