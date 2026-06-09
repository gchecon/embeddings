Abaixo está um **manual prático de uso do `jinaai/jina-embeddings-v3` em Python**, com foco em embeddings locais, RAG e armazenamento no Qdrant.

# Manual de uso do `jinaai/jina-embeddings-v3`

## 1. Visão geral

O `jinaai/jina-embeddings-v3` é um modelo multilíngue de embeddings textuais com **1024 dimensões por padrão**, suporte a contexto de até **8192 tokens**, aproximadamente **570 milhões de parâmetros** e adaptadores LoRA específicos para tarefas como recuperação, classificação, clusterização e comparação textual. Ele foi projetado para uso multilíngue e recuperação de documentos longos, sendo adequado para RAG em português brasileiro e inglês técnico. ([arXiv][1])

A forma mais simples de uso local é por meio da biblioteca `sentence-transformers`, carregando o modelo com `trust_remote_code=True`, pois o modelo possui implementação própria hospedada no Hugging Face. ([Hugging Face][2])

## 2. Instalação

```bash
pip install sentence-transformers qdrant-client torch
```

Para uso com GPU Nvidia, instale uma versão do PyTorch compatível com sua versão de CUDA. Em CPU o modelo funciona, mas será sensivelmente mais lento.

## 3. Carregamento do modelo

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "jinaai/jina-embeddings-v3",
    trust_remote_code=True,
    device="cuda"  # use "cpu" se não houver GPU
)
```

### Parâmetros principais do `SentenceTransformer`

| Parâmetro            | Uso                                             | Recomendação                                |
| -------------------- | ----------------------------------------------- | ------------------------------------------- |
| `model_name_or_path` | Nome do modelo no Hugging Face ou caminho local | `"jinaai/jina-embeddings-v3"`               |
| `trust_remote_code`  | Permite executar o código customizado do modelo | Necessário para este modelo                 |
| `device`             | Define onde o modelo roda                       | `"cuda"` para GPU Nvidia, `"cpu"` para CPU  |
| `revision`           | Fixa uma versão específica do modelo            | Útil em produção                            |
| `token`              | Token Hugging Face, se necessário               | Normalmente dispensável para modelo público |

Em ambiente produtivo, é prudente fixar `revision`, porque atualizações no repositório do modelo podem alterar comportamento, dependências ou resultados.

## 4. Geração de embeddings

```python
textos = [
    "A inteligência artificial pode apoiar a pesquisa em documentos jurídicos.",
    "Sistemas RAG combinam busca vetorial com modelos de linguagem."
]

vetores = model.encode(
    textos,
    task="retrieval.passage",
    normalize_embeddings=True,
    batch_size=16,
    show_progress_bar=True
)
```

## 5. Parâmetros do `encode`

| Parâmetro              | O que faz                                       | Recomendação prática                          |
| ---------------------- | ----------------------------------------------- | --------------------------------------------- |
| `sentences`            | Texto ou lista de textos a converter em vetores | Use lista para processamento em lote          |
| `task`                 | Seleciona o adaptador LoRA da tarefa            | Essencial no Jina v3                          |
| `batch_size`           | Quantidade de textos processados por lote       | Comece com 8, 16 ou 32                        |
| `normalize_embeddings` | Normaliza os vetores para norma 1               | Use `True` com distância cosseno              |
| `show_progress_bar`    | Mostra barra de progresso                       | Use `True` em indexações longas               |
| `convert_to_numpy`     | Retorna `numpy.ndarray`                         | Padrão adequado para Qdrant                   |
| `convert_to_tensor`    | Retorna tensor PyTorch                          | Use só se continuar no PyTorch                |
| `precision`            | Quantização do vetor gerado                     | Use `"float32"` inicialmente                  |
| `truncate_dim`         | Reduz a dimensionalidade via Matryoshka         | Use apenas se quiser economizar armazenamento |
| `device`               | Dispositivo de inferência no momento do encode  | Útil para alternar CPU/GPU                    |
| `output_value`         | Tipo de saída                                   | Use `"sentence_embedding"`                    |

A biblioteca `sentence-transformers` documenta parâmetros como `batch_size`, `precision`, `normalize_embeddings` e `truncate_dim` no método `encode`. ([Tessl][3])

## 6. Parâmetro `task`

Este é o parâmetro mais importante no Jina v3. O modelo possui adaptadores LoRA específicos para diferentes usos. ([Hugging Face][4])

| Valor               | Quando usar                                   |
| ------------------- | --------------------------------------------- |
| `retrieval.query`   | Para perguntas, buscas e consultas do usuário |
| `retrieval.passage` | Para documentos, chunks, trechos indexados    |
| `text-matching`     | Para comparar textos simétricos               |
| `classification`    | Para classificação textual                    |
| `separation`        | Para clusterização ou separação semântica     |

Para RAG, a regra principal é:

```python
# Documentos
model.encode(textos_dos_chunks, task="retrieval.passage")

# Perguntas
model.encode(pergunta, task="retrieval.query")
```

Isso ocorre porque recuperação é uma tarefa assimétrica: a pergunta e o documento não têm o mesmo papel semântico. Em outras palavras, “como usar IA em pesquisa jurídica?” e “este artigo discute IA aplicada à pesquisa jurídica” devem ser projetados em regiões compatíveis do espaço vetorial, mas não necessariamente codificados do mesmo modo.

## 7. Parâmetro `normalize_embeddings`

Use:

```python
normalize_embeddings=True
```

quando a coleção do Qdrant usar:

```python
Distance.COSINE
```

Isso normaliza cada vetor para comprimento 1. Na prática, simplifica a comparação por similaridade cosseno e evita diferenças artificiais de magnitude entre vetores.

## 8. Parâmetro `truncate_dim`

O Jina v3 usa **Matryoshka Representation Learning**, permitindo reduzir a dimensionalidade de 1024 para valores menores, como 768, 512, 256, 128, 64 ou 32. ([Jina AI][5])

Exemplo:

```python
vetores = model.encode(
    textos,
    task="retrieval.passage",
    normalize_embeddings=True,
    truncate_dim=512
)
```

Nesse caso, sua coleção no Qdrant também precisa ser criada com `size=512`.

```python
VectorParams(
    size=512,
    distance=Distance.COSINE
)
```

Minha recomendação para o seu caso:

| Cenário                                        |     Dimensão |
| ---------------------------------------------- | -----------: |
| Máxima qualidade                               |         1024 |
| Bom equilíbrio entre qualidade e armazenamento |          768 |
| Base muito grande, com milhões de chunks       |          512 |
| Prototipagem leve                              |          256 |
| Evitaria para RAG técnico                      | 128 ou menor |

O ponto crítico: **não misture vetores de dimensões diferentes na mesma coleção**. Se você indexou documentos com 1024 dimensões, as consultas também precisam gerar vetores de 1024 dimensões.

## 9. Uso com Qdrant

### Criando a coleção

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

client.recreate_collection(
    collection_name="rag_jina_v3",
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    )
)
```

### Inserindo documentos

```python
from qdrant_client.models import PointStruct
import uuid

documentos = [
    {
        "id_documento": "doc_001",
        "titulo": "IA e pesquisa jurídica",
        "texto": "A inteligência artificial pode apoiar a análise de jurisprudência e decisões judiciais."
    },
    {
        "id_documento": "doc_002",
        "titulo": "RAG acadêmico",
        "texto": "Sistemas RAG combinam recuperação semântica, bases vetoriais e modelos de linguagem."
    }
]

textos = [d["texto"] for d in documentos]

vetores = model.encode(
    textos,
    task="retrieval.passage",
    normalize_embeddings=True,
    batch_size=16
)

pontos = []

for documento, vetor in zip(documentos, vetores):
    pontos.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vetor.tolist(),
            payload=documento
        )
    )

client.upsert(
    collection_name="rag_jina_v3",
    points=pontos
)
```

### Consultando

```python
pergunta = "Como IA pode ajudar na análise de jurisprudência?"

vetor_pergunta = model.encode(
    pergunta,
    task="retrieval.query",
    normalize_embeddings=True
)

resultado = client.query_points(
    collection_name="rag_jina_v3",
    query=vetor_pergunta.tolist(),
    limit=5
)

for ponto in resultado.points:
    print("Score:", ponto.score)
    print("Título:", ponto.payload["titulo"])
    print("Texto:", ponto.payload["texto"])
    print()
```

## 10. Exemplo consolidado

```python
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid


COLLECTION_NAME = "rag_jina_v3"
VECTOR_SIZE = 1024


def carregar_modelo():
    return SentenceTransformer(
        "jinaai/jina-embeddings-v3",
        trust_remote_code=True,
        device="cuda"
    )


def criar_colecao(client: QdrantClient):
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )


def gerar_embeddings_documentos(model, textos):
    return model.encode(
        textos,
        task="retrieval.passage",
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=True
    )


def gerar_embedding_pergunta(model, pergunta):
    return model.encode(
        pergunta,
        task="retrieval.query",
        normalize_embeddings=True
    )


def inserir_documentos(client, model, documentos):
    textos = [doc["texto"] for doc in documentos]
    vetores = gerar_embeddings_documentos(model, textos)

    pontos = []

    for doc, vetor in zip(documentos, vetores):
        pontos.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vetor.tolist(),
                payload=doc
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=pontos
    )


def pesquisar(client, model, pergunta, limite=5):
    vetor = gerar_embedding_pergunta(model, pergunta)

    return client.query_points(
        collection_name=COLLECTION_NAME,
        query=vetor.tolist(),
        limit=limite
    )


def main():
    model = carregar_modelo()
    client = QdrantClient(url="http://localhost:6333")

    criar_colecao(client)

    documentos = [
        {
            "id_documento": "doc_001",
            "titulo": "IA e jurisprudência",
            "texto": "A inteligência artificial pode ser usada para extrair padrões de decisões judiciais."
        },
        {
            "id_documento": "doc_002",
            "titulo": "Embeddings em RAG",
            "texto": "Embeddings permitem representar documentos como vetores para busca semântica."
        },
        {
            "id_documento": "doc_003",
            "titulo": "Anarquismo e tecnologia",
            "texto": "Tecnologias descentralizadas podem apoiar formas alternativas de organização social."
        }
    ]

    inserir_documentos(client, model, documentos)

    pergunta = "Como encontrar decisões judiciais semelhantes usando IA?"

    resultados = pesquisar(client, model, pergunta)

    for item in resultados.points:
        print(f"Score: {item.score:.4f}")
        print(f"Título: {item.payload['titulo']}")
        print(f"Texto: {item.payload['texto']}")
        print()


if __name__ == "__main__":
    main()
```

## 11. Configuração recomendada para RAG em português brasileiro

Para o seu caso, eu usaria inicialmente:

```python
model.encode(
    textos,
    task="retrieval.passage",
    normalize_embeddings=True,
    batch_size=16,
    truncate_dim=None
)
```

E no Qdrant:

```python
VectorParams(
    size=1024,
    distance=Distance.COSINE
)
```

Essa configuração privilegia qualidade. Só reduziria `truncate_dim` para 768 ou 512 se a base crescesse muito e o custo de armazenamento ou RAM passasse a ser um problema real.

## 12. Cuidados importantes

Não misture modelos diferentes na mesma coleção vetorial. Uma coleção criada com `jinaai/jina-embeddings-v3` não deve receber vetores de `text-embedding-3-small`, `bge-m3`, `multilingual-e5-large` ou outro modelo.

Não misture tarefas de indexação. Se os documentos foram indexados com `task="retrieval.passage"`, mantenha esse padrão para todos os documentos da coleção.

Não altere `truncate_dim` depois da coleção criada. Se você começou com 1024 dimensões e depois decide usar 512, crie outra coleção e reindexe tudo.

Não confunda comparação simétrica com busca. Para RAG, use `retrieval.query` e `retrieval.passage`. Para comparar duas frases em pé de igualdade, use `text-matching`.

## 13. Estrutura de payload sugerida

Para um sistema RAG mais sério, eu evitaria guardar apenas o texto. Usaria algo assim:

```python
payload = {
    "document_id": "artigo_001",
    "chunk_id": 12,
    "titulo": "Título do artigo",
    "autor": "Nome do autor",
    "ano": 2024,
    "pagina_inicio": 5,
    "pagina_fim": 6,
    "fonte": "arquivo.pdf",
    "texto": "Conteúdo do chunk"
}
```

Isso facilita rastreabilidade, citação, filtros por metadados e reconstrução posterior do contexto.

## 14. Escolha final recomendada

Para começar com `jinaai/jina-embeddings-v3` em Qdrant, a configuração mais segura é:

```python
task documentos = "retrieval.passage"
task perguntas = "retrieval.query"
dimensão = 1024
normalize_embeddings = True
distance = COSINE
batch_size = 16
precision = "float32"
truncate_dim = None
```

Essa combinação é a mais conservadora tecnicamente: preserva qualidade máxima, mantém compatibilidade semântica entre perguntas e documentos, e evita perdas prematuras por redução dimensional.

[1]: https://arxiv.org/abs/2409.10173?utm_source=chatgpt.com "jina-embeddings-v3: Multilingual Embeddings With Task LoRA"
[2]: https://huggingface.co/jinaai/jina-embeddings-v3?utm_source=chatgpt.com "jinaai/jina-embeddings-v3"
[3]: https://tessl.io/registry/tessl/pypi-sentence-transformers/files/docs/core-transformers.md?utm_source=chatgpt.com "5.1.0 • pypi-sentence-transformers • tessl • Registry"
[4]: https://huggingface.co/docs/transformers/en/model_doc/jina_embeddings_v3?utm_source=chatgpt.com "JinaEmbeddingsV3"
[5]: https://jina.ai/models/jina-embeddings-v3/?utm_source=chatgpt.com "jina-embeddings-v3 - Search Foundation Models"
