# Mad Dog Mock — Documentação Oficial

> **Versão**: 1.0 • **Última atualização**: 27/08/2025  
> **Descrição**: Mad Dog Mock é uma API web para criação de **mocks HTTP dinâmicos**, organizados por **cenários** com *basepath* próprio, **Swagger por cenário**, **CRUD completo**, **variações de retorno por condição** (headers, query, path, JSONPath em body, e *claims* de **JWT OpenID**), e armazenamento **em memória** ou **externo** (cache NoSQL/in-memory).

---

## Sumário
- [1. Visão Geral](#1-visão-geral)
- [2. Conceitos](#2-conceitos)
- [3. Pré-requisitos](#3-pré-requisitos)
- [4. Endpoints de Administração (CRUD)](#4-endpoints-de-administra%C3%A7%C3%A3o-crud)
  - [4.1. Cenários](#41-cen%C3%A1rios)
  - [4.2. Mocks](#42-mocks)
- [5. DSL de Condições & Variantes de Retorno](#5-dsl-de-condi%C3%A7%C3%B5es--variantes-de-retorno)
- [6. Swagger por Cenário](#6-swagger-por-cen%C3%A1rio)
- [7. JWT (OpenID) — Validação e Uso em Condições](#7-jwt-openid--valida%C3%A7%C3%A3o-e-uso-em-condi%C3%A7%C3%B5es)
- [8. Exemplos Práticos (cURL)](#8-exemplos-pr%C3%A1ticos-curl)
  - [8.1. Criar cenário](#81-criar-cen%C3%A1rio)
  - [8.2. Criar mocks (GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS)](#82-criar-mocks-getpostputpatchdeleteheadoptions)
  - [8.3. Variações por header/query/path/body/JWT](#83-varia%C3%A7%C3%B5es-por-headerquerypathbodyjwt)
  - [8.4. Retorno com dados "dinâmicos"](#84-retorno-com-dados-din%C3%A2micos)
- [9. Erros Padrão](#9-erros-padr%C3%A3o)
- [10. Armazenamento & Cache](#10-armazenamento--cache)
- [11. Deploy (resumo)](#11-deploy-resumo)

---

## 1. Visão Geral
O **Mad Dog Mock** permite criar **endpoints HTTP fictícios** sem codar rotas manualmente. Você cadastra **cenários** (cada um com um `basepath` único) e **mocks** dentro deles (método + URI), define **variantes de retorno** com **condições**, e obtém um **Swagger** exclusivo por cenário para testar.

**Destaques:**
- Paths dinâmicos por cenário (`/{basepath}/...`).
- CRUD de cenários e mocks (listar, consultar, incluir, alterar, excluir).
- Swagger geral (CRUD) e Swagger por cenário (somente execução dos mocks daquele cenário).
- Variações por **header**, **query**, **path params**, **JSONPath** no body, e **claims** de **JWT OpenID** (inclusive `realm_access`/`resource_access`).  
- Armazenamento em **memória**, **Redis** ou **Mongo** (configurável).
- Exclusão de cenário remove todos os mocks vinculados (cascata).
- Nenhum campo de entrada é obrigatório (você fornece só o que precisa).

---

## 2. Conceitos

### Cenário
Agrupador de mocks com um **`basepath`** único (ex.: `bank/v1`). O **`basepath` é o identificador** do cenário. Cada cenário tem **Swagger próprio**.

### Mock
Um endpoint **HTTP** caracterizado por: `método`, `uri` (relativa ao `basepath`), **parâmetros** (query/path/header), **contentType** de requisição e resposta, **tags**, **nome/descrição** e **variantes de retorno**.

### Variante
Uma possível **resposta** para o mock com: `status`, `headers`, `contentType`, `payload` e uma **condição** (opcional). O mecanismo avalia as variantes na ordem; a **primeira condição satisfeita** é retornada. Se nenhuma condicionar casar, usa-se a variante **default** (aquela sem condição).

---

## 3. Pré-requisitos

- **Para criar um cenário:**
  - `basepath` (único no sistema, ex.: `bank/v1`)
  - `name` (opcional) e `description` (opcional)
  - (Opcional) **JWT config**:
    - `jwtIssuerUrl` (https do OpenID Issuer)
    - `jwtLocation` (`header` ou `cookie`)
    - Se `header`: `jwtHeaderName` (ex.: `Authorization`) e `jwtBearer` (true/false)
    - Se `cookie`: `jwtCookieName` (nome do cookie com o token)
  - Observação: se configurar JWT no cenário, a validação **só é executada** quando o token **estiver presente**; se **declarado** e **não presente** na requisição do mock, retorna erro específico.

- **Para criar um mock:**
  - `scenarioBasepath` (já cadastrado)
  - `method` (`GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS`)
  - `uri` (ex.: `/accounts/{id}`)
  - (Opcional) `name`, `description`, `tags`
  - (Opcional) `request` (contentType e schema/params)
  - Uma ou mais **`responses`** (variantes) com `status`, `contentType`, `payload`, `headers`, `description` e `condition` (opcional).  
  - **Regra anti-duplicidade**: **POST** para criar mock com mesmo `(scenarioBasepath, method, uri)` é recusado; use **PUT** para alterar.

---

## 4. Endpoints de Administração (CRUD)

> Swagger geral dos CRUDs: **`/docs`** (possui *External Docs* → guia HTML).

### 4.1. Cenários

- **Listar cenários**  
  `GET /api/scenarios`  
  Resposta inclui `basepath`, `name`, `description`, `swaggerUrl` (por cenário).

- **Criar cenário**  
  `POST /api/scenarios`  
  Body (exemplo mínimo):
  ```json
  {
    "basepath": "bank/v1",
    "name": "Banking",
    "description": "Cenário de APIs bancárias",
    "jwt": {
      "issuerUrl": "https://issuer.example.com/realms/demo",
      "location": "header",
      "headerName": "Authorization",
      "bearer": true
    }
  }
  ```
  Regras:
  - `basepath` **único**. Se já existir, retorna erro.

- **Obter cenário**  
  `GET /api/scenarios/{basepath}`

- **Atualizar cenário**  
  `PUT /api/scenarios/{basepath}`

- **Excluir cenário (em cascata)**  
  `DELETE /api/scenarios/{basepath}`  
  Remove também todos os mocks do cenário.

---

### 4.2. Mocks

- **Listar mocks**  
  `GET /api/mocks?scenario={basepath}`

- **Criar mock**  
  `POST /api/mocks`  
  Campos principais:
  ```json
  {
    "scenarioBasepath": "bank/v1",
    "method": "GET",
    "uri": "/accounts/{id}",
    "name": "Consultar conta",
    "description": "Retorna os dados da conta",
    "tags": ["accounts", "read"],
    "request": {
      "contentType": "application/json",
      "query": [{"name":"verbose","required":false,"type":"string"}],
      "headers": [{"name":"X-Tenant","required":false,"type":"string"}],
      "path": [{"name":"id","required":false,"type":"string"}]
    },
    "responses": [
      {
        "description": "Retorno padrão",
        "status": 200,
        "contentType": "application/json",
        "headers": {"X-Mock":"default"},
        "payload": {"id":"{{path.id}}","balance":100.0}
      },
      {
        "description": "Somente admin (JWT realm_access)",
        "status": 200,
        "contentType": "application/json",
        "headers": {"X-Mock":"admin"},
        "condition": "jwt.realm_access.roles contains 'admin'",
        "payload": {"id":"{{path.id}}","balance":5000.0,"tier":"ADMIN"}
      }
    ]
  }
  ```

  **Regra anti-duplicidade**: Se já existir mock com `(scenarioBasepath, method, uri)`, o **POST** falha e a mensagem orienta usar **PUT**.

- **Obter mock**  
  `GET /api/mocks/{mockId}`

- **Atualizar mock**  
  `PUT /api/mocks/{mockId}`

- **Excluir mock**  
  `DELETE /api/mocks/{mockId}`

---

## 5. DSL de Condições & Variantes de Retorno

Você define **`condition`** (string) em cada variante. Operadores suportados (expressão *case-sensitive*):
- `==`, `!=`, `in`, `contains`, `startswith`, `endswith`, `~` (regex)
- Parênteses para agrupamento: `( ... )`
- `and`, `or`, `not`

**Contexto disponível na expressão:**
- `header.<Nome>` — cabeçalhos (ex.: `header.X-Env`)
- `query.<nome>` — query params (ex.: `query.debug`)
- `path.<nome>` — path params (ex.: `path.id`)
- `body` — JSON completo do corpo
- `jsonpath('<expr>')` — extrai via JSONPath (ex.: `jsonpath('$.user.role') == 'premium'`)
- `jwt.<claim>` — claims do token (payload)
- `jwt.header.<campo>` — cabeçalhos do token (ex.: `jwt.header.kid`)
- **Realm/Resource roles**:  
  - `jwt.realm_access.roles contains 'admin'`  
  - `jwt.resource_access['app-client'].roles contains 'writer'`

**Precedência:** A primeira variante cuja `condition` for **true** é escolhida. Se nenhuma casar, usa a **default** (sem `condition`).

---

## 6. Swagger por Cenário

- **UI**: `GET /scenarios/{basepath}/docs`  
- **OpenAPI**: `GET /scenarios/{basepath}/openapi.json`

O Swagger do cenário traz:
- **basepath**, **nome** e **descrição** do cenário
- mocks agrupados por **tags**
- para cada mock: **métodos suportados**, **parâmetros** (query, path, header), **payloads** de requisição e **exemplos de resposta**

---

## 7. JWT (OpenID) — Validação e Uso em Condições

- Configure no **cenário** a origem do token (`header` ou `cookie`) e o **Issuer URL** (HTTPS).
- **Validação só ocorre se o token estiver presente** no local definido.
- Casos de erro:
  1. **Token declarado mas ausente** → 400 com mensagem específica
  2. **Erro de integração** (rede/Issuer indisponível) → 502/503 com detalhe
  3. **Token inválido** (assinatura/expiração/issuer) → 401 com motivo
- Após validado, o token fica disponível como `jwt.*` no contexto da **condition**.

---

## 8. Exemplos Práticos (cURL)

> Base local: `http://localhost:8080`

### 8.1. Criar cenário
```bash
curl -X POST http://localhost:8080/api/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "basepath":"bank/v1",
    "name":"Banking",
    "description":"APIs bancárias de exemplo",
    "jwt": {
      "issuerUrl": "https://issuer.example.com/realms/demo",
      "location": "header",
      "headerName": "Authorization",
      "bearer": true
    }
  }'
```

### 8.2. Criar mocks (GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS)

#### GET
```bash
curl -X POST http://localhost:8080/api/mocks \
  -H "Content-Type: application/json" \
  -d '{
    "scenarioBasepath":"bank/v1",
    "method":"GET",
    "uri":"/accounts/{id}",
    "name":"Get Account",
    "tags":["accounts"],
    "responses":[
      {"status":200,"contentType":"application/json","payload":{"id":"{{path.id}}","ok":true}}
    ]
  }'
```

#### POST
```bash
curl -X POST http://localhost:8080/api/mocks \
  -H "Content-Type: application/json" \
  -d '{
    "scenarioBasepath":"bank/v1",
    "method":"POST",
    "uri":"/transfers",
    "name":"Create Transfer",
    "responses":[
      {"status":201,"contentType":"application/json","payload":{"transferId":"T-{{uuid}}","status":"CREATED"}}
    ]
  }'
```

#### PUT
```bash
curl -X POST http://localhost:8080/api/mocks \
  -H "Content-Type: application/json" \
  -d '{
    "scenarioBasepath":"bank/v1",
    "method":"PUT",
    "uri":"/accounts/{id}",
    "name":"Update Account",
    "responses":[
      {"status":200,"contentType":"application/json","payload":{"id":"{{path.id}}","updated":true}}
    ]
  }'
```

#### PATCH
```bash
curl -X POST http://localhost:8080/api/mocks \
  -H "Content-Type: application/json" \
  -d '{
    "scenarioBasepath":"bank/v1",
    "method":"PATCH",
    "uri":"/accounts/{id}",
    "name":"Patch Account",
    "responses":[
      {"status":200,"contentType":"application/json","payload":{"id":"{{path.id}}","patched":true}}
    ]
  }'
```

#### DELETE
```bash
curl -X POST http://localhost:8080/api/mocks \
  -H "Content-Type: application/json" \
  -d '{
    "scenarioBasepath":"bank/v1",
    "method":"DELETE",
    "uri":"/accounts/{id}",
    "name":"Delete Account",
    "responses":[
      {"status":204,"contentType":"application/json","payload":{}}
    ]
  }'
```

#### HEAD
```bash
curl -X POST http://localhost:8080/api/mocks \
  -H "Content-Type: application/json" \
  -d '{
    "scenarioBasepath":"bank/v1",
    "method":"HEAD",
    "uri":"/health",
    "name":"Head Health",
    "responses":[
      {"status":200,"headers":{"X-Health":"ok"}}
    ]
  }'
```

#### OPTIONS
```bash
curl -X POST http://localhost:8080/api/mocks \
  -H "Content-Type: application/json" \
  -d '{
    "scenarioBasepath":"bank/v1",
    "method":"OPTIONS",
    "uri":"/accounts",
    "name":"Options Accounts",
    "responses":[
      {"status":204,"headers":{"Allow":"GET,POST,PUT,PATCH,DELETE,HEAD,OPTIONS"}}
    ]
  }'
```

### 8.3. Variações por header/query/path/body/JWT

- **Por header**: `condition: "header.X-Env == 'prod'"`
- **Por query**: `condition: "query.debug == 'true'"`
- **Por path**: `condition: "path.id == '42'"`
- **Por JSONPath no body**: `condition: "jsonpath('$.user.role') == 'premium'"`
- **Por JWT**: `condition: "jwt.realm_access.roles contains 'admin'"`

Exemplo completo:
```json
"responses": [
  {
    "description": "Ambiente prod",
    "status": 200,
    "condition": "header.X-Env == 'prod'",
    "payload": {"env":"prod"}
  },
  {
    "description": "Debug ligado",
    "status": 200,
    "condition": "query.debug == 'true'",
    "payload": {"debug":true}
  },
  {
    "description": "Somente admin",
    "status": 200,
    "condition": "jwt.realm_access.roles contains 'admin'",
    "payload": {"role":"admin"}
  },
  {
    "description": "Padrão",
    "status": 200,
    "payload": {"ok":true}
  }
]
```

### 8.4. Retorno com dados "dinâmicos"

Se o retorno do mock estiver habilitado para **template**, você pode usar *placeholders* no `payload` (renderização tipo Jinja):

- `{{path.id}}`, `{{query.page}}`, `{{header.X_Tenant}}`
- `{{jsonpath("$.user.name")}}`
- `{{jwt.sub}}`, `{{jwt.preferred_username}}`
- utilitários: `{{now}}`, `{{uuid}}`, `{{randint(1,999)}}`

Exemplo:
```json
{
  "status": 200,
  "contentType": "application/json",
  "payload": {
    "id": "{{path.id}}",
    "user": "{{jsonpath('$.user.name')}}",
    "who": "{{jwt.preferred_username}}",
    "ts": "{{now}}",
    "reqId": "{{uuid}}"
  }
}
```

> Observação: caso o template não esteja ativado no ambiente, os *placeholders* serão tratados como texto literal.

---

## 9. Erros Padrão

- **Mock duplicado (POST)**: 409 com mensagem orientando a usar **PUT**.
- **JWT declarado mas ausente**: 400
  ```json
  {"error":"jwt_missing","message":"Token JWT não encontrado no header/cookie configurado"}
  ```
- **Erro na integração com Issuer**: 502/503
  ```json
  {"error":"issuer_unreachable","message":"Falha ao consultar JWKS do issuer","detail":"<motivo>"}
  ```
- **Falha de validação do token**: 401
  ```json
  {"error":"jwt_invalid","message":"Assinatura/expiração/issuer inválido"}
  ```
- **Cenário basepath duplicado**: 409  
- **Cenário não encontrado / Mock não encontrado**: 404

---

## 10. Armazenamento & Cache

- **InMemory** (padrão): simples e rápido para dev.
- **Redis/Mongo**: configure via variáveis de ambiente (exemplo no Docker Compose).  
- A API mantém *cache* de mocks por cenário; invalidações ocorrem nas operações de CRUD.

---

## 11. Deploy (resumo)

- **Docker Compose**: `docker compose up --build` (Mongo/Redis opcionais).
- **OpenShift 4**: use a imagem Docker publicada e configure Route para a porta da aplicação.  
- Endpoints úteis:
  - Swagger CRUD: `/docs`
  - Lista cenários: `/api/scenarios`
  - Swagger do cenário: `/scenarios/{basepath}/docs`

---

**Dúvidas?** Consulte o Swagger geral (`/docs`) e o Swagger do seu cenário.  
Se precisar de exemplos adicionais (latência simulada, headers customizados etc.), crie variantes com `headers` e/ou `condition` específicas.
