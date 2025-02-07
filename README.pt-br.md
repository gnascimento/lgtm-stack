# 🔍 Stack LGTM para Kubernetes

<br>

<div align="center">
    <a href="README.md">🇺🇸 English</a> | <a href="README.pt-br.md">🇧🇷 Português (Brasil)</a>
</div>
<br>

Guia completo de implantação de uma plataforma de observabilidade para Kubernetes. A stack LGTM, da Grafana Labs, combina as melhores ferramentas open-source para fornecer visibilidade abrangente do sistema, consistindo em:

- **Loki**: Armazenamento e gerenciamento de logs
- **Tempo**: Armazenamento e gerenciamento de traces distribuídos
- **Mimir**: Armazenamento de métricas de longo prazo
- **Grafana**: Interface e Dashboards

## Arquitetura

A arquitetura da stack LGTM integra todos os componentes para fornecer uma solução completa de observabilidade:

![Arquitetura LGTM](./assets/images/lgtm.jpg)

Cada componente (Loki, Grafana, Tempo, Mimir) é executado no Kubernetes com seu próprio backend de armazenamento. Por exemplo, estamos usando o GCP Cloud Storage como exemplo, mas eles também suportam AWS/Azure como backends. Para desenvolvimento local, podemos usar o MinIO.

A stack também inclui três componentes opcionais:
- Prometheus: coleta métricas do cluster (CPU/Memória) e envia para o Mimir
- Promtail: agente que captura logs de contêineres e envia para o Loki
- OpenTelemetry Collector: roteia todos os dados de telemetria para os backends apropriados, atuando como um hub central

## Início Rápido

### ✨ Pré-requisitos
- Helm v3+ (gerenciador de pacotes)
- kubectl
- Para GCP: CLI gcloud com permissões de proprietário do projeto

### Requisitos de Hardware

Desenvolvimento local:
- 2-4 CPUs
- 8 GB RAM
- 50 GB de espaço em disco

Configuração de produção:
- Pode variar muito dependendo da quantidade de dados e tráfego, é recomendado começar com uma configuração pequena e escalar conforme necessário, para configurações pequenas com 20 milhões de logs consumidos por dia, 11 mil métricas por minuto e 3 milhões de spans por dia, a seguinte configuração é recomendada:
  - 8 CPUs
  - 24 GB RAM
  - 100 GB de espaço em disco (SSD, não conta para backends de armazenamento)

### Configuração
```bash
# Adicionar repositórios e criar namespace
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
kubectl create ns monitoring
```

### Escolha Seu Ambiente

#### Desenvolvimento Local (k3s, minikube)

Para cenários de teste e desenvolvimento local. Usa armazenamento local via MinIO.

```bash
helm install lgtm --version 2.1.0 -n monitoring \
  grafana/lgtm-distributed -f helm/values-lgtm.local.yaml
```

#### Configuração GCP Produção

Para ambientes de produção, usando recursos GCP para armazenamento e monitoramento.

1. Configure os recursos GCP:

```bash
# Configure seu ID de projeto
export PROJECT_ID=your-project-id

# Crie buckets com sufixo aleatório
export BUCKET_SUFFIX=$(openssl rand -hex 4 | tr -d "\n")
for bucket in logs traces metrics metrics-admin; do
  gsutil mb -p ${PROJECT_ID} -c standard -l us-east1 gs://lgtm-${bucket}-${BUCKET_SUFFIX}
done

# Atualize os nomes dos buckets na configuração
sed -i -E "s/(bucket_name:\s*lgtm-[^[:space:]]+)/\1-${BUCKET_SUFFIX}/g" helm/values-lgtm.gcp.yaml

# Crie e configure a conta de serviço
gcloud iam service-accounts create lgtm-monitoring \
    --display-name "LGTM Monitoring" \
    --project ${PROJECT_ID}

# Configure permissões
for bucket in logs traces metrics metrics-admin; do 
  gsutil iam ch serviceAccount:lgtm-monitoring@${PROJECT_ID}.iam.gserviceaccount.com:admin \
    gs://lgtm-${bucket}-${BUCKET_SUFFIX}
done

# Crie a chave da conta de serviço e o secret
gcloud iam service-accounts keys create key.json \
    --iam-account lgtm-monitoring@${PROJECT_ID}.iam.gserviceaccount.com
kubectl create secret generic lgtm-sa --from-file=key.json -n monitoring
```

2. Instale a stack LGTM:

Altere o values-lgtm.gcp.yaml de acordo com suas necessidades antes de aplicar, como configuração de ingress, requisitos de recursos, etc.

```bash
helm install lgtm --version 2.1.0 -n monitoring \
  grafana/lgtm-distributed -f helm/values-lgtm.gcp.yaml
```

## Instalar dependências

```bash
# Instalar Promtail para coletar logs de contêineres
# Verifique se você está usando runtime Docker ou CRI-O
## Runtime Docker
kubectl apply -f manifests/promtail.docker.yaml
## Runtime CRI-O
kubectl apply -f manifests/promtail.cri.yaml

# Instalar prometheus operator para coleta de métricas
helm install prometheus-operator --version 66.3.1 -n monitoring \
  prometheus-community/kube-prometheus-stack -f helm/values-prometheus.yaml

# Instalar dashboards kubernetes para grafana
kubectl apply -f manifests/kubernetes-dashboards.yaml
```

## Testes

### Acessar Grafana
```bash
# Acessar dashboard
kubectl port-forward svc/lgtm-grafana 3000:80 -n monitoring

# Obter credenciais de senha
kubectl get secret --namespace monitoring lgtm-grafana -o jsonpath="{.data.admin-password}" | base64 --decode
```
- Usuário padrão: `admin`
- URL de acesso: http://localhost:3000
- Verifique os dashboards padrão do Grafana e a aba Explore

### Teste dos Componentes

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
2. Vá para Explore > Selecione a fonte de dados Loki
3. Consulte usando labels: `{app="test", level="info"}`
4. Você deve ver sua mensagem de teste nos resultados

Se você instalou o promtail, você também pode verificar os logs dos contêineres na aba Explore.

#### Tempo (Traces)

```bash
# Encaminhar porta do Tempo
kubectl port-forward svc/lgtm-tempo-distributor 4318:4318 -n monitoring

# Gerar traces de exemplo com nome de serviço 'test'
docker run --add-host=host.docker.internal:host-gateway --env=OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 jaegertracing/jaeger-tracegen -service test -traces 10
```

Para verificar:
1. Vá para Explore > Selecione a fonte de dados Tempo
2. Pesquise por Nome do Serviço: 'test'
3. Você deve ver 10 traces com diferentes spans

#### Mimir (Métricas)

Se o operador Prometheus foi instalado, temos uma instância rodando dentro do cluster enviando métricas básicas (CPU/Memória) para o Mimir, você pode verificar as métricas já no Grafana:

1. Acesse o Grafana
2. Vá para Explore > Selecione a fonte de dados Mimir
3. Experimente estas consultas de exemplo:
   - `rate(container_cpu_usage_seconds_total[5m])` - Uso de CPU
   - `container_memory_usage_bytes` - Uso de memória do contêiner

### Dicas de Solução de Problemas

Se os componentes não estiverem funcionando:

1. Verifique o status dos pods:
```bash
kubectl get pods -n monitoring
```

2. Visualize os logs dos componentes:
```bash
# Para o Loki
kubectl logs -l app.kubernetes.io/name=loki -n monitoring

# Para o Tempo
kubectl logs -l app.kubernetes.io/name=tempo -n monitoring

# Para o Mimir
kubectl logs -l app.kubernetes.io/name=mimir -n monitoring
```

> Consulte a documentação oficial de cada componente para mais etapas de solução de problemas.

## Componentes Adicionais

### OpenTelemetry Collector

O OpenTelemetry Collector atua como um hub central para todos os dados de telemetria:

```bash
# Instalar OpenTelemetry Collector
kubectl apply -f manifests/otel-collector.yaml
```

#### Configuração de Endpoints

| Tipo de Dados | Protocolo | Endpoint | Porta |
|---------------|-----------|----------|-------|
| Traces | gRPC | otel-collector | 4317 |
| Traces | HTTP | otel-collector | 4318 |
| Metrics | gRPC | otel-collector | 4317 |
| Metrics | HTTP | otel-collector | 4318 |
| Logs | HTTP | otel-collector | 3100 |

#### Integração com Componentes

1. **Configuração do Promtail**
   - Edite `manifests/promtail.yaml`
   - Atualize a seção clients:
   ```yaml
   clients:
     - url: http://otel-collector:3100/loki/api/v1/push
   ```

2. **Integração com Aplicações**
   - Use SDKs OpenTelemetry
   - Configure endpoint: `otel-collector:4317` para gRPC
   - Para HTTP: `http://otel-collector:4318`

#### Verificação

Verifique se o collector está recebendo dados:
```bash
# Visualizar logs do collector
kubectl logs -l app=otel-collector -n monitoring
```

#### Configuração Extra

##### Personalização de Labels do Loki

Para adicionar novos labels aos logs no Loki através do OpenTelemetry Collector:

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
        value: facility, level, source, host, app, namespace, pod, container, job, your_label
```

> Após modificar o ConfigMap, reinicie o pod do collector para aplicar as mudanças:
> ```bash
> kubectl rollout restart daemonset/otel-collector -n monitoring
> ```

## Desinstalação

```bash
# Remover stack LGTM
helm uninstall lgtm -n monitoring

# Remover prometheus operator 
helm uninstall prometheus-operator -n monitoring

# Remover namespace
kubectl delete ns monitoring

# Remover promtail & otel-collector 
kubectl delete -f manifests/promtail.yaml
kubectl delete -f manifests/otel-collector.yaml

# Para configuração GCP, limpeza:
for bucket in logs traces metrics metrics-admin; do
  gsutil rm -r gs://lgtm-${bucket}-${BUCKET_SUFFIX}
done

gcloud iam service-accounts delete lgtm-monitoring@${PROJECT_ID}.iam.gserviceaccount.com
```
````
