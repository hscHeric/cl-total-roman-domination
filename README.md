# cl-total-roman-domination

Estudo experimental e implementações de métodos exatos e metaheurísticos (incluindo BRKGA) para o **Total Roman Domination Problem (TRDP)** sobre instâncias reais e sintéticas.

---

## Início rápido: como baixar o repositório e gerar o dataset

### 1. Baixar o repositório

Clone o repositório já trazendo o submódulo [`external/graph-instances`](external/graph-instances):

```bash
# Via SSH (recomendado)
git clone --recurse-submodules git@github.com:hscHeric/cl-total-roman-domination.git
cd cl-total-roman-domination
```

Ou via HTTPS:

```bash
git clone --recurse-submodules https://github.com/hscHeric/cl-total-roman-domination.git
cd cl-total-roman-domination
```

Se você já clonou sem `--recurse-submodules`, inicialize o submódulo com:

```bash
git submodule update --init --recursive
```

### 2. Instalar as ferramentas do ambiente (`mise`)

O projeto gerencia `cmake`, `conan`, `ninja` e `python` via [`mise`](https://mise.jdx.dev/) (veja [`mise.toml`](mise.toml)):

```bash
mise trust
mise install
```

### 3. Gerar ou reproduzir o dataset

Na raiz do projeto, execute **apenas**:

```bash
mise run dataset
```

Esse comando cuida de tudo automaticamente (inicializa o submódulo e o `.venv` se necessário, baixa/converte as 4 bases reais, gera as 4 bases sintéticas, filtra vértices isolados, seleciona 30 instâncias representativas por base, copia os 240 arquivos `.col` para `dataset/processed/<base>/instances/` e valida os hashes **SHA-256**):

- Se `dataset/processed/<base>/metadata.json` **já existir** (padrão ao clonar o repositório) → **reproduz exatamente** os 240 grafos usando os parâmetros e seeds versionados.
- Se `dataset/processed/<base>/metadata.json` **não existir** → **gera um novo dataset do zero** com novas seeds aleatórias e grava os novos `metadata.json` e `selection.csv`.

Se quiser escolher explicitamente o modo:

```bash
# Reproduzir exatamente o dataset atual a partir dos metadata.json (mesmas seeds e SHA-256)
mise run dataset:reproduce

# Gerar um NOVO dataset do zero (novas seeds aleatórias nas sintéticas;
# atualiza instances/*.col, metadata.json e selection.csv em dataset/processed/)
mise run dataset:generate

# Atalhos parciais e verificação
mise run dataset:reproduce:synthetic   # reproduzir apenas as 4 bases sintéticas
mise run dataset:reproduce:real        # reproduzir apenas as 4 bases reais
mise run dataset:verify                # apenas verificar a integridade SHA-256 dos .col
```

Opções extras podem ser passadas via `--` ao script [`scripts/instances/reproduce_dataset.py`](scripts/instances/reproduce_dataset.py):

```bash
# Pré-visualizar todos os comandos sem executar nada
mise run dataset -- --dry-run
mise run dataset:generate -- --dry-run

# Processar apenas bases específicas (ex.: cubic e erdos_renyi)
mise run dataset -- --datasets cubic erdos_renyi
mise run dataset:generate -- --synthetic-only

# Reaproveitar downloads já presentes em external/graph-instances/datasets/<base>/raw/
mise run dataset:reproduce:real -- --skip-download
```

---

## Estrutura do repositório

```text
.
├── dataset/
│   └── processed/
│       └── <base>/
│           ├── instances/     # Arquivos .col (ignorados pelo Git; gerados via `mise run dataset`)
│           ├── metadata.json  # Proveniência, seeds, parâmetros e hashes SHA-256
│           └── selection.csv  # 16 features estruturais, clusters K-Means e PCA 2D
├── docs/                      # Notas técnicas e documentação do projeto
├── experiments/
│   ├── configs/               # Configurações de execução
│   ├── suites/                # Definições de suites de instâncias
│   └── tuning/                # Configurações de calibração (BRKGA e método secundário)
├── external/
│   └── graph-instances/       # Submódulo gerador/conversor/seletor de grafos
├── results/                   # Resultados brutos e agregados dos experimentos
├── scripts/
│   ├── analysis/              # Análise estatística, tabelas e gráficos
│   ├── instances/             # Reprodução, geração e verificação SHA-256 do dataset
│   └── tuning/                # Scripts de calibração de hiperparâmetros
├── src/
│   ├── common/                # Parser DIMACS .col, CLI, RNG e utilitários compartilhados
│   ├── problem/               # Modelo TRDP, validador de factibilidade e busca local
│   └── methods/
│       ├── exact/             # Formulação/solver exato (MILP)
│       ├── brkga/             # Método principal (BRKGA)
│       └── secondary/         # Método secundário de comparação
├── tests/                     # Testes unitários e de pipeline
└── mise.toml                  # Versões fixadas de CMake, Conan, Ninja, Python e tasks
```

---

## Dataset (`dataset/processed/`)

O benchmark é composto por **240 grafos simples, não-direcionados e sem vértices isolados** no formato DIMACS `.col`, divididos igualmente em **8 famílias** (**30 instâncias representativas por base** selecionadas via K-Means sobre 16 features estruturais com transformação `log1p` e padronização `StandardScaler`, usando `--seed 42`):

| Base | Tipo | Pool Elegível | Pool Clusterizado | Selecionados | `n` Único | `n` Mín | `n` Máx | Silhouette |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `harwell_boeing` | Real (NIST Matrix Market) | 133 | 133 | 30 | 30 | 62 | 44.609 | `0.3176` |
| `dimacs` | Benchmark clássico | 78 | 78 | 30 | 15 | 28 | 4.000 | `0.4109` |
| `bhoslib` | Benchmark difícil | 36 | 36 | 30 | 8 | 450 | 4.000 | `0.0964` |
| `snap` | Real (redes grandes) | 1.010 | 85\* | 30 | 30 | 8 | 3.774.768 | `0.3344` |
| `cubic` | Sintético (3-regular) | 106 | 106 | 30 | 30 | 100 | 9.312 | `0.3919` |
| `erdos_renyi` | Sintético ($G(n,p)$, $\bar{d}=12$) | 102 | 102 | 30 | 30 | 100 | 5.490 | `0.1630` |
| `barabasi_albert` | Sintético ($m=4$) | 103 | 103 | 30 | 30 | 100 | 8.910 | `0.2481` |
| `watts_strogatz` | Sintético ($k=6, p=0.15$) | 98 | 98 | 30 | 30 | 100 | 6.265 | `0.2008` |

\* No `snap`, séries temporais repetitivas (`as-733`, `as-caida`, `oregon1`, `oregon2`, `comm-f2f-resistance`) são limitadas a no máximo 2 snapshots representativos cada (`--max-per-series 2`) antes do K-Means global.

### Por que os arquivos `.col` não são versionados no Git?

A pasta `dataset/processed/` completa soma **~1,8 GB** e contém 4 grafos do SNAP acima do limite rígido de **100 MB por arquivo** do GitHub (`as-skitter.col`, `cit-Patents.col`, `gplus_combined.col` e `soc-pokec-relationships.col`), além de exceder a cota gratuita de 1 GB do Git LFS.

Por isso, o `.gitignore` ignora apenas `dataset/processed/*/instances/*.col`, enquanto **toda a proveniência e verificabilidade permanecem versionadas no Git**:
- `dataset/processed/<base>/metadata.json`: parâmetros, seeds exatas de geração/seleção, estatísticas do K-Means/PCA e **hash SHA-256** de cada um dos 240 arquivos `.col`.
- `dataset/processed/<base>/selection.csv`: tabela completa com as 16 features, atribuição de clusters e projeção PCA 2D.
- `external/graph-instances`: submódulo fixado no commit exato usado na geração e seleção.

---

### Alternativas para obter ou distribuir o dataset

#### Empacotar / restaurar via arquivo compactado (ex.: GitHub Releases ou Zenodo)

Para distribuir os 240 grafos prontos (sem precisar rebaixar/reconverter o SNAP), basta compactar em um único arquivo (~350–400 MB, aceito gratuitamente em **GitHub Releases** até 2 GB ou no **Zenodo**):

```bash
# Empacotar
tar -I 'zstd -19' -cf dataset-processed-v1.tar.zst dataset/processed/

# Restaurar na raiz do projeto e validar hashes SHA-256
tar -I zstd -xf dataset-processed-v1.tar.zst
mise run dataset:verify
```

#### Execução manual passo a passo (sem `mise`)

```bash
# 1. Preparar o ambiente do submódulo (Python 3.14 recomendado)
cd external/graph-instances
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Baixar e converter as 4 bases reais (removendo vértices isolados)
python graph_instances.py download harwell-boeing
python graph_instances.py download dimacs
python graph_instances.py download bhoslib
python graph_instances.py download snap
python graph_instances.py convert all --remove-isolated

# 3. Gerar as 4 bases sintéticas com as seeds exatas registradas em metadata.json
#    (remova --seed <...> caso queira gerar novas instâncias com seeds aleatórias)
python graph_instances.py generate cubic           --doubling 100 1.045 106 --count 1 --seed 1589853731 --remove-isolated
python graph_instances.py generate erdos-renyi     --doubling 100 1.045 103 --avg-degree 12 --count 1 --seed 232044735 --remove-isolated
python graph_instances.py generate barabasi-albert --doubling 100 1.045 103 --m 4 --count 1 --seed 1715692963 --remove-isolated
python graph_instances.py generate watts-strogatz  --doubling 100 1.045 98  --k 6 --p-rewire 0.15 --count 1 --seed 1845657283 --remove-isolated

# 4. Garantir ausência de vértices isolados e selecionar os 30 representantes de cada base
python graph_instances.py filter all --remove-isolated
for ds in harwell-boeing dimacs bhoslib snap cubic erdos-renyi barabasi-albert watts-strogatz; do
  python graph_instances.py select "$ds" --count 30 --seed 42
done

# 5. Copiar os .col selecionados para dataset/processed/ e validar SHA-256
for ds in harwell_boeing dimacs bhoslib snap cubic erdos_renyi barabasi_albert watts_strogatz; do
  mkdir -p "../../dataset/processed/$ds/instances"
  cp "datasets/$ds/selected/"*.col "../../dataset/processed/$ds/instances/"
done

cd ../..
python3 scripts/instances/reproduce_dataset.py --verify-only
```
