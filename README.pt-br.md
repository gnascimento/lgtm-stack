<br>

<div align="center">
    <a href="README.md">🇺🇸 English</a> | <a href="README.pt-br.md">🇧🇷 Português (Brasil)</a>
</div>
<br>

# 🔍 Stack LGTM para Kubernetes

## Introdução

A stack LGTM, da Grafana Labs, combina as melhores ferramentas open-source para fornecer visibilidade completa do sistema, consistindo em:

- **Loki**: Sistema de Agregação de logs https://grafana.com/oss/loki/
- **Grafana**: Sistema para Interface & Dashboards https://grafana.com/oss/grafana/
- **Tempo**: Armazenamento e gerenciamento de traces distribuídos https://grafana.com/oss/tempo/
- **Mimir**: Armazenamento de métricas a longo prazo para o Prometheus https://grafana.com/oss/mimir/


Com essa stack, temos uma solução completa de observabilidade que cobre logs, métricas e traces, com suporte para alta disponibilidade e escalabilidade, todos os dados ficam centralizados no Grafana para facilitar a análise e correlação de eventos, e por utilizar armazenamento em bucket (object storage) como backend, a solução se torna muito mais econômica em comparação com outras que necessitam de bancos de dados dedicados ou discos persistentes.

## Índice

<details>
- [Arquitetura](#arquitetura)
  - [Requisitos de Hardware](#requisitos-de-hardware)
- [Início Rápido](#-início-rápido)
  - [Pré-requisitos](#-pré-requisitos)
  - [Instalação](#instalação)
    - [Opção 1: Makefile](#opção-1-makefile)
    - [Opção 2: Instalação Manual](#opção-2-instalação-manual)
      - [Configuração](#configuração)
      - [Escolha seu Ambiente](#escolha-seu-ambiente)
        - [Local](#local-k3s-minikube)
        - [Configuração para Produção na GCP](#configuração-para-produção-na-gcp)
- [Instalação de Dependências](#instalação-de-dependências-opcional)
- [Testando](#testando)
  - [Acesso ao Grafana](#acesso-ao-grafana)
  - [Enviando Dados](#enviando-dados)
    - [Loki (Logs)](#loki-logs)
    - [Tempo (Traces)](#tempo-traces)
    - [Mimir (Métricas)](#mimir-métricas)
- [OpenTelemetry](#opentelemetry)
  - [OpenTelemetry Collector](#opentelemetry-collector)
  - [Integração com Flask App](#integração-com-flask-app)
  - [Testando a Integração](#testando-a-integração)
  - [Configuração Adicional](#configuração-adicional)
    - [Personalização de Labels no Loki](#personalização-de-labels-no-loki)
- [Desinstalação](#desinstalação)
</details>

## Arquitetura

![Arquitetura LGTM](./assets/images/lgtm.jpg)

A arquitetura da stack LGTM em um ambiente Kubernetes segue um fluxo bem definido de coleta, processamento e visualização de dados:

1. As aplicações enviam dados de telemetria para um agente, nesse caso o OpenTelemetry Collector.

2. O OpenTelemetry Collector atua como hub central, roteando cada tipo de dado para seu backend específico:
  * Loki: para processamento de logs
  * Mimir: para armazenamento de métricas
  * Tempo: para análise de traces
3. Os dados são armazenados em um Object Storage, com buckets dedicados para cada ferramenta

4. O Grafana é a interface, aonde todos os dados são consultados, permitindo dashboards e alertas unificados

A arquitetura também inclui quatro componentes opcionais:
- Prometheus: coleta métricas personalizadas de aplicações e do cluster e envia para o Mimir
- Kube-state-metrics: coleta métricas (CPU/Memória etc) dos serviços/apps através do API server e expõe para o Prometheus
- Promtail: agente que captura logs dos containers e envia para o Loki

### Requisitos de Hardware

Local:
- 2-4 CPUs
- 8 GB RAM

Ambiente de produção:
- Pode variar muito dependendo da quantidade de dados e tráfego, é recomendado começar com uma configuração pequena e escalar conforme necessário, para ambientes pequenos e médios a seguinte configuração é recomendada (mínimo):
  - 8 CPUs
  - 24 GB RAM
  - 100 GB de espaço em disco (SSD, não conta para backends de armazenamento)

  
## 🚀 Início Rápido

### ✨ Pré-requisitos
- [Helm v3+](https://helm.sh/docs/intro/install/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
  - Para instalação local: [k3s](https://k3s.io/) ou [minikube](https://minikube.sigs.k8s.io/docs/start/) kubernetes cluster configurado
- Para GCP: [gcloud CLI](https://cloud.google.com/sdk/docs/install)

> **Note**: Esse guia usa o helm chart [lgtm-distributed](https://artifacthub.io/packages/helm/grafana/lgtm-distributed) oficial do Grafana para deployment.

### Opção 1: Makefile

Para simplificar o processo de instalação, você pode usar os comandos do Makefile:

```bash
# Clonar repositório
git clone git@github.com:daviaraujocc/lgtm-stack.git
cd lgtm-stack
make install-local # Para testes locais, para usar GCP cloud storage use make install-gcp e defina a variável PROJECT_ID
```

Isso irá instalar a stack LGTM com a configuração padrão para teste local com as dependências (promtail, dashboards, prometheus, MiniO ). Para personalizar a instalação, você pode editar o arquivo `helm/values-lgtm.local.yaml` antes de instalar.

### Opção 2: Instalação Manual

### Configuração
```bash
# Clonar repositório
git clone git@github.com:daviaraujocc/lgtm-stack.git
cd lgtm-stack

# Adicionar repositórios e criar namespace
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
kubectl create ns monitoring

# Instale o prometheus operator para coleta de métricas e CRDs
helm install prometheus-operator --version 66.3.1 -n monitoring \
  prometheus-community/kube-prometheus-stack -f helm/values-prometheus.yaml
```

### Escolha seu Ambiente

#### Local (k3s, minikube)

Para cenários de teste local. Utiliza armazenamento local via MinIO.

```bash
helm install lgtm --version 2.1.0 -n monitoring \
  grafana/lgtm-distributed -f helm/values-lgtm.local.yaml
```

#### Configuração para Produção na GCP

Para ambientes de produção, utilizando recursos da GCP para armazenamento e monitoramento.

1. Configure recursos GCP:

```bash
# Definir ID do projeto
export PROJECT_ID=seu-projeto-id

# Criar buckets com sufixo aleatório
export BUCKET_SUFFIX=$(openssl rand -hex 4 | tr -d "\n")
for bucket in logs traces metrics metrics-admin; do
  gsutil mb -p ${PROJECT_ID} -c standard -l us-east1 gs://lgtm-${bucket}-${BUCKET_SUFFIX}
done

# Atualizar nomes dos buckets na configuração
sed -i -E "s/(bucket_name:\s*lgtm-[^[:space:]]+)/\1-${BUCKET_SUFFIX}/g" helm/values-lgtm.gcp.yaml

# Criar e configurar conta de serviço
gcloud iam service-accounts create lgtm-monitoring \
    --display-name "LGTM Monitoring" \
    --project ${PROJECT_ID}

# Configurar permissões
for bucket in logs traces metrics metrics-admin; do 
  gsutil iam ch serviceAccount:lgtm-monitoring@${PROJECT_ID}.iam.gserviceaccount.com:admin \
    gs://lgtm-${bucket}-${BUCKET_SUFFIX}
done

# Criar chave da conta de serviço e secret
gcloud iam service-accounts keys create key.json \
    --iam-account lgtm-monitoring@${PROJECT_ID}.iam.gserviceaccount.com
kubectl create secret generic lgtm-sa --from-file=key.json -n monitoring
```

2. Instalar stack LGTM:

Você pode ajustar o arquivo values-lgtm.gcp.yaml de acordo com suas necessidades antes de aplicar, como configuração de ingress, requisitos de recursos, etc.

```bash
helm install lgtm --version 2.1.0 -n monitoring \
  grafana/lgtm-distributed -f helm/values-lgtm.gcp.yaml
```

## Instalação de Dependências (opcional)

```bash
# Instalar Promtail para coletar logs dos containers (opcional)
## Ambiente Docker
kubectl apply -f manifests/promtail.docker.yaml
## Ambiente CRI
# kubectl apply -f manifests/promtail.cri.yaml
```

## Testando

Depois de instalar a stack LGTM, verifique se todos os componentes estão em execução:

```bash
# Verificar pods em execução
kubectl get pods -n monitoring

# Para checar logs dos componentes

# Loki
kubectl logs -l app.kubernetes.io/name=loki -n monitoring

# Tempo
kubectl logs -l app.kubernetes.io/name=tempo -n monitoring

# Mimir
kubectl logs -l app.kubernetes.io/name=mimir -n monitoring
```

Siga as instruções abaixo para acessar e testar cada componente:

### Acesso ao Grafana
```bash
# Acessar dashboard
kubectl port-forward svc/lgtm-grafana 3000:80 -n monitoring

# Obter senha
kubectl get secret --namespace monitoring lgtm-grafana -o jsonpath="{.data.admin-password}" | base64 --decode
```
- Usuário padrão: `admin`
- URL de acesso: http://localhost:3000

### Enviando Dados

Após a instalação, verifique se cada componente está funcionando corretamente:

#### Loki (Logs)
Teste a ingestão e consulta de logs:

```bash
# Encaminhar porta do Loki
kubectl port-forward svc/lgtm-loki-distributor 3100:3100 -n monitoring

# Enviar log de teste com timestamp e labels
curl -XPOST http://localhost:3100/loki/api/v1/push -H "Content-Type: application/json" -d '{
  "streams": [{
    "stream": { "app": "test", "level": "info" },
    "values": [[ "'$(date +%s)000000000'", "Mensagem de log de teste" ]]
  }]
}'
```

Para verificar:
1. Abra o Grafana (http://localhost:3000)
2. Vá para Explore > Selecione fonte de dados Loki
3. Consulte usando labels: `{app="test", level="info"}`
4. Você deverá ver sua mensagem de teste nos resultados

Se você instalou o Promtail, você também pode verificar os logs dos containers na aba Explore.

#### Tempo (Traces)

Como o tempo é compatível com o protocolo OTLP da OpenTelemetry, usaremos o Jaeger Trace Generator, uma ferramenta que gera traces de exemplo que também envia os dados usando OTLP.

```bash
# Encaminhar porta do Tempo
kubectl port-forward svc/lgtm-tempo-distributor 4318:4318 -n monitoring

# Gerar traces de exemplo com nome de serviço 'test'
docker run --add-host=host.docker.internal:host-gateway --env=OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 jaegertracing/jaeger-tracegen -service test -traces 10
```

Para verificar:
1. Vá para Explore > Selecione fonte de dados Tempo
2. Pesquise pelo Nome do Serviço: 'test'
3. Você deverá ver 10 traces com diferentes spans

#### Mimir (Métricas)

Como temos uma instância do Prometheus rodando dentro do cluster enviando métricas básicas (CPU/Memória) para o Mimir, você pode verificar as métricas já no Grafana:

1. Acesse o Grafana
2. Vá para Explore > Selecione a fonte de dados Mimir
3. Experimente estas consultas de exemplo:
   - `rate(container_cpu_usage_seconds_total[5m])` - Uso de CPU
   - `container_memory_usage_bytes` - Uso de memória do container

Você também pode fazer o push de métricas personalizadas para o Mimir usando o Prometheus Pushgateway, para o endpoint `http://lgtm-mimir-nginx.monitoring:80/api/v1/push`.

## OpenTelemetry

OpenTelemetry é um conjunto de APIs, bibliotecas, agentes e instrumentação para fornecer observabilidade para software nativo de nuvem. Consiste em três componentes principais:

- **OpenTelemetry SDK**: Bibliotecas para instrumentar aplicações para coletar dados de telemetria (traces, métricas, logs).
- **OpenTelemetry Collector**: Um agente agnóstico de fornecedor que coleta, processa e exporta dados de telemetria para backends.
- **OpenTelemetry Protocol (OTLP)**: Um padrão para troca de dados de telemetria entre aplicações e backends.

Nesta configuração, usaremos o OpenTelemetry Collector para rotear dados de telemetria para os backends apropriados (Loki, Tempo, Mimir).

### OpenTelemetry Collector

Para instalar o OpenTelemetry Collector:

```bash
# Instalar OpenTelemetry Collector
kubectl apply -f manifests/otel-collector.yaml
```

Verifique se o collector está em execução:

```bash
kubectl get pods -l app=otel-collector
kubectl logs -l app=otel-collector
```

### Integração com Flask App

Usaremos uma aplicação Flask pré-instrumentada (código fonte em `flask-app/`) que gera traces, métricas e logs usando OpenTelemetry.

A aplicação expõe um endpoint `/random` que retorna números aleatórios e gera dados de telemetria. O endpoint padrão usado para enviar dados de telemetria será `http://otel-collector:4318`.

1. Implante a aplicação de exemplo:
```bash
# Implantar aplicação de exemplo
kubectl apply -f manifests/app/flask-app.yaml
```

2. Verifique a implantação da aplicação:
```bash
kubectl get pods -l app=flask-app 
kubectl get svc flask-app-service 
```

3. Aplique o PodMonitor para coleta de métricas:
```bash
kubectl apply -f manifests/app/podmonitor.yaml
```

### Testando a integração

1. Gere tráfego para a aplicação:
```bash
# Obtenha a URL da aplicação
# Port-forward da aplicação
kubectl port-forward svc/flask-app 8000:8000 -n monitoring

# Envie requisições para gerar dados de telemetria
for i in {1..50}; do
  curl http://localhost:8000/random
  sleep 0.5
done
```

2. Verifique os dados de telemetria gerados no Grafana:

**Traces (Tempo):**

1. Vá para Explore > Selecione a fonte de dados Tempo

2. Pesquise por Service Name: flask-app

3. Você deverá ver traces com operações GET /random

**Métricas (Mimir):**

1. Vá para Explore > Selecione a fonte de dados Mimir

2. Experimente estas consultas:
```promql
# Contagem total de requisições
rate(request_count_total[5m])
```

**Logs (Loki):**

1. Vá para Explore > Selecione a fonte de dados Loki

2. Consulte usando labels:

```logql
{job="flask-app"}
```
Você deverá ver logs estruturados da aplicação.

#### Configuração Adicional

##### Personalização de Labels no Loki

Caso você tenha novos labels que deseja adicionar aos logs no Loki através do OpenTelemetry Collector, você precisa realizar a seguinte configuração:

1. Edite o ConfigMap `otel-collector-config`
2. Localize a seção `processors.attributes/loki`
3. Adicione seus labels personalizados à lista `loki.attribute.labels`:

```yaml
processors:
  attributes/loki:
    actions:
      - action: insert
        key: loki.format
        value: raw
      - action: insert
        key: loki.attribute.labels
        value: facility, level, source, host, app, namespace, pod, container, job, seu_label
```

> Após modificar o ConfigMap, reinicie o pod do collector para aplicar as mudanças:
> ```bash
> kubectl rollout restart daemonset/otel-collector -n monitoring
> ```

## Desinstalação

```bash
# Usando makefile
make uninstall

# ou manualmente

# Remover stack LGTM
helm uninstall lgtm -n monitoring

# Remover prometheus operator 
helm uninstall prometheus-operator -n monitoring

# Remover namespace
kubectl delete ns monitoring

# Remover promtail & otel-collector 
kubectl delete -f manifests/promtail.yaml
kubectl delete -f manifests/otel-collector.yaml

# Para ambiente GCP, limpeza:
for bucket in logs traces metrics metrics-admin; do
  gsutil rm -r gs://lgtm-${bucket}-${BUCKET_SUFFIX}
done

gcloud iam service-accounts delete lgtm-monitoring@${PROJECT_ID}.iam.gserviceaccount.com
```